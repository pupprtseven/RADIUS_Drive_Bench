from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from ..config import BenchmarkConfig
from ..constants import ACC_FACTOR_EFFECTIVENESS_GT, DecisionLabel, LT_ELE_CHOICES, POST_DEC_TO_LEVEL
from ..models import PipelineResult, ScoreResult
from ..utils.choice_resolvers import resolve_post_dec
from ..utils.text_norm import normalize_choice_text, normalize_tax_code, parse_bool
from ..llm.judge import JudgeService


class ScoreCalculator:
    """Scoring logic (kept intentionally close to the original implementation)."""

    def __init__(self, config: BenchmarkConfig, judge: Optional[JudgeService] = None):
        self.config = config
        self.judge = judge

    @staticmethod
    def validate_pre_decision(vx: Any, ay: Any, valid_controls: List[Dict]) -> DecisionLabel:
        try:
            vx_int = int(vx) if vx is not None else 0
            ay_int = int(ay) if ay is not None else 0
        except (TypeError, ValueError):
            return DecisionLabel.INVALID

        if not valid_controls:
            return DecisionLabel.INVALID

        for item in valid_controls:
            try:
                item_vx = int(item.get('vx', float('inf')))
                item_ay = int(item.get('ay', float('inf')))
                if item_vx == vx_int and item_ay == ay_int:
                    return DecisionLabel.from_string(str(item.get('label', '0')))
            except (TypeError, ValueError):
                continue

        return DecisionLabel.INVALID

    @staticmethod
    def get_optimal_control_from_valid_controls(valid_controls: List[Dict]) -> Optional[tuple[int, int]]:
        if not valid_controls:
            return None
        for item in valid_controls:
            try:
                if str(item.get("label", "0")) == "1":
                    return int(item.get("vx", 0)), int(item.get("ay", 0))
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _is_none_lt_ele(choice_text: str, idx: Optional[int]) -> bool:
        if idx is not None and idx == 0:
            return True
        t = (choice_text or "").strip().lower()
        if not t:
            return False
        return (t == "none") or ("none of the above" in t) or ("no long-tail element" in t)

    @staticmethod
    def _resolve_gt_levels(gt: dict) -> tuple[str, str, str]:
        l3 = normalize_tax_code(gt.get("level3", ""))
        l2 = normalize_tax_code(gt.get("level2", ""))
        l1 = normalize_tax_code(gt.get("level1", ""))
        if l3 or l2 or l1:
            if l3 and not l2:
                parts = l3.split(".")
                l2 = ".".join(parts[:2]) if len(parts) >= 2 else ""
            if (l2 or l3) and not l1:
                base = l2 or l3
                l1 = base.split(".")[0] if base else ""
            return str(l3), str(l2), str(l1)

        tax = normalize_tax_code(gt.get("taxonomy") or gt.get("taxonomy_code") or gt.get("tax") or "")
        if tax:
            parts = tax.split(".")
            l1 = parts[0] if len(parts) >= 1 else ""
            l2 = ".".join(parts[:2]) if len(parts) >= 2 else l1
            l3 = ".".join(parts[:3]) if len(parts) >= 3 else l2
            return l3, l2, l1

        return "", "", ""

    @staticmethod
    def _resolve_gt_lt_ele(gt: Dict) -> tuple[str, Optional[int]]:
        lt = gt.get("lt_ele") or gt.get("lt_ele_choice") or gt.get("lt_ele_text") or ""
        lt = normalize_choice_text(lt)
        if lt:
            return lt, None

        idx = gt.get("lt_ele_idx", None)
        try:
            if idx is not None:
                idx_int = int(idx)
                if 0 <= idx_int < len(LT_ELE_CHOICES):
                    return LT_ELE_CHOICES[idx_int], idx_int
        except Exception:
            pass

        return "", None

    @staticmethod
    def _resolve_gt_acc_factors_multi(gt_dict: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        acc_multi = gt_dict.get("acc_factors_multi")
        if isinstance(acc_multi, dict) and acc_multi:
            return acc_multi, "gt.acc_factors_multi"

        acc = gt_dict.get("acc_factors") or gt_dict.get("acc_factors_list")
        items: List[str] = []
        if isinstance(acc, list):
            items = [str(x).strip() for x in acc if str(x).strip()]
        elif isinstance(acc, str):
            items = [x.strip() for x in re.split(r"[\n;；,，]+", acc) if x.strip()]

        if len(items) < 3:
            return {}, f"gt.acc_factors_invalid(len={len(items)})"

        return {
            "group1_choice": items[0],
            "group2_choice": items[1],
            "group3_choice": items[2],
        }, "gt.acc_factors(list)->multi"

    def _score_acc_factors_multi(self, pred_multi: Dict, gt_multi: Dict, weight_override: Optional[float] = None) -> tuple[int, str]:
        if not gt_multi:
            return 0, "No GT acc_factors_multi"
        total_w = float(weight_override if weight_override is not None else (self.config.score_acc_factors or 0))
        w1 = int(round(total_w * (3 / 15)))
        w2 = int(round(total_w * (6 / 15)))
        w3 = int(max(0, total_w - w1 - w2))
        weights = {"group1_choice": w1, "group2_choice": w2, "group3_choice": w3}
        pts = 0
        detail: List[str] = []
        for key, w in weights.items():
            p = (pred_multi.get(key) or "").strip().lower()
            g = (gt_multi.get(key) or "").strip().lower()
            if not g:
                detail.append(f"{key}: GT missing (+0)")
                continue
            if p and p == g:
                pts += w
                detail.append(f"{key}: match (+{w})")
            else:
                detail.append(f"{key}: pred={p or '∅'} gt={g} (+0)")
        return pts, "; ".join(detail)

    @staticmethod
    def _normalize_effective_prediction(raw_val: Any) -> set[int]:
        """Convert predicted effective-factor selection to a canonical {1,2,3} set."""
        normalized: set[int] = set()
        if isinstance(raw_val, (list, tuple, set)):
            candidates = raw_val
        elif isinstance(raw_val, dict):
            # Accept {"1": true/false, "2": ..., "3": ...} style
            candidates = [k for k, v in raw_val.items() if v is True or str(v).lower() in {"true", "1", "yes"}]
        elif isinstance(raw_val, str):
            parts = re.split(r"[,\s;/；，]+", raw_val.strip())
            candidates = [p for p in parts if p]
        else:
            candidates = []

        for item in candidates:
            try:
                v = int(item)
            except Exception:
                continue
            if v in {1, 2, 3}:
                normalized.add(v)
        return normalized

    @staticmethod
    def _gt_effective_set(gt_level3: str) -> set[int]:
        norm = normalize_tax_code(gt_level3)
        if not norm:
            return set()
        return set(ACC_FACTOR_EFFECTIVENESS_GT.get(norm, set()))

    @staticmethod
    def _strip_leading_numbers(text: Any) -> str:
        if text is None:
            return ""
        return re.sub(r'^[\d\.]+', '', str(text)).strip()

    @staticmethod
    def _map_post_choice_to_level(choice: Any) -> Optional[int]:
        """Replicate change_post mapping from score.py with a small fallback."""
        if choice is None:
            return None
        raw = str(choice).strip()
        if not raw:
            return None
        if raw.isdigit():
            try:
                v = int(raw)
                if 1 <= v <= 5:
                    return v
            except Exception:
                pass

        norm = normalize_choice_text(raw)
        mapping = {
            "low-speed straight passage": 1,
            "slow down and take a detour": 1,
            "wait for avoidance and proceed straight ahead": 2,
            "wait for avoidance and take a detour": 2,
            "wait for avoidance and depending on the situation proceed straight ahead or take a detour": 3,
            "park safely and request instructions": 4,
            "park safely and replan the route": 4,
            "emergency evacuation based on actual conditions": 5,
        }
        if norm in mapping:
            return mapping[norm]

        # Fallback to the canonical mapping to stay compatible with any newer choices.
        if raw in POST_DEC_TO_LEVEL:
            return POST_DEC_TO_LEVEL[raw]
        return POST_DEC_TO_LEVEL.get(norm)

    @staticmethod
    def _score_pre_decision_label(label: DecisionLabel, weights: Dict[str, int]) -> tuple[int, str]:
        if label == DecisionLabel.OPTIMAL:
            return weights.get("label1", 0), f"Label 1 -> +{weights.get('label1', 0)}"
        if label == DecisionLabel.SAFE:
            return weights.get("label2", 0), f"Label 2 -> +{weights.get('label2', 0)}"
        if label == DecisionLabel.HAZARDOUS:
            return weights.get("label4", 0), f"Label 4 -> +{weights.get('label4', 0)}"
        return 0, f"Label {label.value} -> +0"

    @staticmethod
    def _score_post_decision_simple(pred_level: Optional[int], gt_level: Optional[int], weight_override: Optional[float] = None) -> tuple[int, str]:
        """Score post-decision per the simplified rules in score.py."""
        total_w = float(weight_override or 0)
        if not gt_level or pred_level is None:
            return 0, f"Missing post_dec level (pred={pred_level}, gt={gt_level}) -> +0"

        try:
            p = int(pred_level)
            g = int(gt_level)
        except Exception:
            return 0, f"Invalid post_dec level (pred={pred_level}, gt={gt_level}) -> +0"

        if p == g:
            pts = int(round(total_w))
            return pts, f"Exact match (pred={p}, gt={g}) -> +{pts}"

        partial = int(round(total_w * 0.25))  # 5 when weight=20
        if g == 3 and p == 2:
            return partial, f"g=3, pred=2 (slightly more aggressive) -> +{partial}"
        if g == 4 and p in (2, 3):
            return partial, f"g=4, pred={p} (more aggressive) -> +{partial}"

        if p > g:
            penalty_step = total_w / 4.0
            pts = int(max(0, round(total_w - (p - g) * penalty_step)))
            return pts, f"More conservative (pred={p}, gt={g}) -> +{pts}"

        return 0, f"More aggressive (pred={p}, gt={g}) -> +0"

    def _score_effective_factors(self, pred_set: set[int], gt_set: set[int], weight_override: Optional[float] = None) -> tuple[int, str]:
        if gt_set is None:
            return 0, "GT effective set unavailable"
        total_w = float(weight_override if weight_override is not None else (self.config.score_acc_effective or 0))
        if not gt_set:
            if not pred_set:
                return int(total_w), f"GT empty set; predicted none -> +{int(total_w)}"
            return 0, f"GT empty set; predicted extras={sorted(pred_set)} -> +0"

        if pred_set and not pred_set.issubset(gt_set):
            return 0, f"Selected extra factors {sorted(pred_set - gt_set)} beyond GT {sorted(gt_set)} -> +0"

        correct = len(pred_set & gt_set)
        total = len(gt_set)
        if correct == 0:
            return 0, f"No effective factors matched; GT={sorted(gt_set)}"

        pct = correct / total
        pts = int(round(total_w * pct))
        detail = f"{correct}/{total} effective factors matched -> +{pts}"
        if pred_set != gt_set:
            missing = sorted(gt_set - pred_set)
            detail += f" (missing {missing})"
        return pts, detail

    def _score_post_levels(self, pred_level: Optional[int], gt_level: Optional[int], weight_override: Optional[float] = None) -> tuple[int, str, Optional[int]]:
        w_post = float(weight_override if weight_override is not None else (self.config.score_post_dec or 0))
        if not pred_level or not gt_level:
            return 0, f"Missing post_dec level (pred={pred_level}, gt={gt_level})", None

        try:
            pred_level = int(pred_level)
            gt_level = int(gt_level)
        except Exception:
            return 0, f"Invalid level values (pred={pred_level}, gt={gt_level})", None

        def _layer(level: int) -> int:
            if level == 1:
                return 0
            if level in (2, 3, 4):
                return 1
            if level == 5:
                return 2
            return -1

        p_layer = _layer(pred_level)
        g_layer = _layer(gt_level)
        if p_layer < 0 or g_layer < 0:
            return 0, f"Unknown abstract layer: pred=L{pred_level}, gt=L{gt_level}", None

        decision_style = p_layer - g_layer

        penalty_per_layer = w_post / 4.0
        if p_layer == g_layer:
            pts = int(round(w_post))
            detail = (
                f"Same abstract layer: pred=L{pred_level}(A{p_layer}) "
                f"gt=L{gt_level}(A{g_layer}) -> +{pts}"
            )
        elif p_layer > g_layer:
            if g_layer == 0 and p_layer == 2:
                pts = 0
                detail = (
                    "Upward jump across two abstract layers ([1] -> [5]): "
                    f"pred=L{pred_level}(A{p_layer}) gt=L{gt_level}(A{g_layer}) -> +0"
                )
            else:
                pts = int(round(penalty_per_layer))
                detail = (
                    f"More conservative (upward cross {p_layer - g_layer} abstract layer): "
                    f"pred=L{pred_level}(A{p_layer}) gt=L{gt_level}(A{g_layer}) -> +{pts}"
                )
        else:
            diff = g_layer - p_layer
            pts = int(max(0, w_post - diff * penalty_per_layer))
            detail = (
                f"More aggressive (downward cross {diff} abstract layer): "
                f"pred=L{pred_level}(A{p_layer}) gt=L{gt_level}(A{g_layer}) -> +{pts}"
            )

        return pts, detail, decision_style

    @staticmethod
    def _resolve_pred_post_level(pred: PipelineResult) -> Optional[int]:
        level_candidate = getattr(pred, "post_dec_level", None) or getattr(pred, "post_dec_level_model", None)
        try:
            if level_candidate:
                level_int = int(level_candidate)
                if 1 <= level_int <= 5:
                    return level_int
        except Exception:
            level_candidate = None

        pred_dec_raw = getattr(pred, "post_dec", "") or ""
        if str(pred_dec_raw).strip().isdigit():
            try:
                v = int(str(pred_dec_raw).strip())
                if 1 <= v <= 5:
                    return v
            except Exception:
                pass

        pred_dec, _ = resolve_post_dec(pred_dec_raw, allow_fuzzy=True)
        if pred_dec in POST_DEC_TO_LEVEL:
            return POST_DEC_TO_LEVEL[pred_dec]
        return None

    def _resolve_gt_post_level(self, gt: Dict) -> Optional[int]:
        level_candidate = (
            gt.get("post_decision_level")
            or gt.get("post_dec_level")
            or gt.get("post_dec_level_gt")
        )
        try:
            if level_candidate is not None:
                lv = int(level_candidate)
                if 1 <= lv <= 5:
                    return lv
        except Exception:
            pass

        gt_dec_raw = gt.get("post_dec", "") or ""
        if str(gt_dec_raw).strip().isdigit():
            try:
                lv = int(str(gt_dec_raw).strip())
                if 1 <= lv <= 5:
                    return lv
            except Exception:
                pass

        gt_dec, _ = resolve_post_dec(gt_dec_raw, allow_fuzzy=True)
        return POST_DEC_TO_LEVEL.get(gt_dec)
    def _judge_post_level(self, pred: PipelineResult, gt: Dict) -> tuple[Optional[int], Optional[LLMJudgeResult]]:
        if self.config.use_llm_judge and self.judge:
            gt_level = self._resolve_gt_post_level(gt)
            jr = self.judge.call("post_level", {
                "level3": str(getattr(pred, "level3", "N/A")),
                "lt_ele": str(getattr(pred, "lt_ele", "N/A")),
                "acc_factors_text": str(getattr(pred, "acc_factors", "N/A")),
                "acc_effective_indices": str(getattr(pred, "acc_factors_effective", [])),
                "post_decision_plan": str(getattr(pred, "post_dec", "N/A")),
                "cot": str(getattr(pred, "COT", "N/A")),
                "gt_post_dec_level": str(gt_level or "N/A"),
            })
            level = jr.score if jr.score else None
            return level, jr

        # LLM judge is required for mapping; without it, skip scoring this dimension.
        return None, None

    def calculate_score(self, pred: PipelineResult, gt: Dict, label: DecisionLabel) -> ScoreResult:
        score = ScoreResult()
        if not gt:
            score.pre_dec_detail = "No ground truth available"
            return score

        gt_level3, gt_level2, gt_level1 = self._resolve_gt_levels(gt)
        gt_lt_ele, _ = self._resolve_gt_lt_ele(gt)

        pred_is_longtail = parse_bool(getattr(pred, "is_longtail", None), default=False)
        gt_is_longtail = parse_bool(gt.get("is_longtail", None), default=True)

        default_weights = {
            "classification": self.config.score_classification or 0,
            "is_longtail": self.config.score_is_longtail or 0,
            "pre_dec": self.config.score_pre_dec or 0,
            "lt_ele": self.config.score_lt_ele or 0,
            "acc_factors": self.config.score_acc_factors or 0,
            "acc_effective": self.config.score_acc_effective or 0,
            "post_dec": self.config.score_post_dec or 0,
        }
        non_lt_weights = {
            "classification": 0,
            "is_longtail": 50,
            "pre_dec": 50,
            "lt_ele": 0,
            "acc_factors": 0,
            "acc_effective": 0,
            "post_dec": 0,
        }

        def _set_max(weights: Dict[str, int]) -> None:
            score.max_per_dim = {k: int(v) for k, v in weights.items()}
            score.max_total_override = sum(score.max_per_dim.values())

        # ---------- Non-longtail GT ----------
        if gt_is_longtail is False:
            _set_max(non_lt_weights)
            # Pre-decision scoring: 50/25/0
            score.pre_dec, score.pre_dec_detail = self._score_pre_decision_label(
                label,
                {"label1": 50, "label2": 50, "label4": 25},
            )
            if not pred_is_longtail:
                score.is_longtail = non_lt_weights["is_longtail"]
                score.is_longtail_detail = f"GT non-longtail, pred non-longtail -> +{score.is_longtail}"
            else:
                score.is_longtail = 0
                score.is_longtail_detail = "GT non-longtail, pred longtail -> +0"
            score.classification_detail = "classification disabled for GT non-longtail"
            score.lt_ele_detail = "lt_ele disabled for GT non-longtail"
            score.acc_factors_detail = "acc_factors disabled for GT non-longtail"
            score.acc_effective_detail = "acc_effective disabled for GT non-longtail"
            score.post_dec_detail = "post_dec disabled for GT non-longtail"
            return score

        # ---------- Longtail GT but pred says non-longtail ----------
        gt_level3_norm = normalize_tax_code(gt_level3)
        if not pred_is_longtail:
            if gt_level3_norm == "2.5.3":
                _set_max(non_lt_weights)
                # Special tolerant branch mirrors score.py's 50/50 split.
                score.pre_dec, score.pre_dec_detail = self._score_pre_decision_label(
                    label,
                    {"label1": 50, "label2": 50, "label4": 25},
                )
                score.is_longtail = non_lt_weights["is_longtail"]
                score.is_longtail_detail = "GT 2.5.3 with pred non-longtail: accept both branches -> +50"
            else:
                _set_max(default_weights)
                score.pre_dec, score.pre_dec_detail = self._score_pre_decision_label(
                    label,
                    {"label1": 15, "label2": 10, "label4": 5},
                )
                score.is_longtail_detail = "GT longtail but pred non-longtail -> +0"
            score.classification_detail = "skipped due to pred is_longtail=False"
            score.lt_ele_detail = "skipped due to pred is_longtail=False"
            score.acc_factors_detail = "skipped due to pred is_longtail=False"
            score.acc_effective_detail = "skipped due to pred is_longtail=False"
            score.post_dec_detail = "skipped due to pred is_longtail=False"
            return score

        # ---------- Longtail GT and pred longtail ----------
        _set_max(default_weights)
        score.is_longtail = default_weights["is_longtail"]
        score.is_longtail_detail = f"GT longtail, pred longtail -> +{score.is_longtail}"

        # Pre-decision: 15/10/5/0
        score.pre_dec, score.pre_dec_detail = self._score_pre_decision_label(
            label,
            {"label1": 15, "label2": 10, "label4": 5},
        )

        # Classification (reuse original taxonomy matching with same weights)
        pred_l3 = normalize_tax_code(getattr(pred, "level3", ""))
        pred_l2 = normalize_tax_code(getattr(pred, "level2", ""))
        pred_l1 = normalize_tax_code(getattr(pred, "level1", ""))
        w_cls = float(default_weights["classification"])
        w_cls_l2 = int(round(w_cls * 2 / 3))
        w_cls_l1 = int(max(0, round(w_cls * 1 / 3)))
        if gt_level3 and pred_l3 == gt_level3:
            score.classification = int(round(w_cls))
            score.classification_detail = f"level3 match ({pred_l3}) -> +{score.classification}"
        elif gt_level2 and pred_l2 == gt_level2:
            score.classification = w_cls_l2
            score.classification_detail = f"level2 match ({pred_l2}) -> +{score.classification} (gt_level3={gt_level3})"
        elif gt_level1 and pred_l1 == gt_level1:
            score.classification = w_cls_l1
            score.classification_detail = f"level1 match ({pred_l1}) -> +{score.classification} (gt_level3={gt_level3})"
        else:
            score.classification = 0
            score.classification_detail = f"no taxonomy match (pred={pred_l3 or pred_l2 or pred_l1}, gt={gt_level3}) -> +0"

        # Long-tail element
        w_lt = int(round(default_weights["lt_ele"]))
        pred_lt_norm = normalize_choice_text(getattr(pred, "lt_ele", "")).lower()
        gt_lt_norm = normalize_choice_text(gt_lt_ele).lower()
        lt_match = bool(pred_lt_norm and gt_lt_norm and (
            pred_lt_norm == gt_lt_norm or (
                pred_lt_norm == "ponding water" and gt_lt_norm == "road surface damage-light"
            )
        ))
        score.lt_ele = w_lt if lt_match else 0
        score.lt_ele_detail = f"pred={pred_lt_norm!r} gt={gt_lt_norm!r} -> +{score.lt_ele}"

        # ACC factors (3/6/6 split, trimming numeric prefixes on predictions)
        gt_acc_multi, gt_acc_src = self._resolve_gt_acc_factors_multi(gt)
        pred_acc_multi = getattr(pred, "acc_factors_multi", {}) or {}
        pred_acc_clean = {k: self._strip_leading_numbers(v) for k, v in pred_acc_multi.items()}
        gt_acc_clean = {k: self._strip_leading_numbers(v) for k, v in gt_acc_multi.items()}
        if default_weights["acc_factors"] <= 0:
            score.acc_factors = 0
            score.acc_factors_detail = "acc_factors disabled (weight=0)"
        else:
            acc_pts, acc_detail = self._score_acc_factors_multi(
                pred_acc_clean, gt_acc_clean, weight_override=default_weights["acc_factors"]
            )
            score.acc_factors = acc_pts
            score.acc_factors_detail = f"{gt_acc_src} | {acc_detail}"

        # Effective factors (reuse original proportional logic)
        if default_weights["acc_effective"] <= 0:
            score.acc_effective = 0
            score.acc_effective_detail = "acc_effective disabled (weight=0)"
        else:
            gt_effective = self._gt_effective_set(gt_level3)
            pred_effective = self._normalize_effective_prediction(getattr(pred, "acc_factors_effective", set()))
            eff_pts, eff_detail = self._score_effective_factors(
                pred_effective, gt_effective, weight_override=default_weights["acc_effective"]
            )
            score.acc_effective = eff_pts
            score.acc_effective_detail = eff_detail

        # Post-decision scoring mirrors change_post logic from score.py
        judged_level, judge_result = self._judge_post_level(pred, gt)
        if judge_result:
            score.post_dec_level_judge = judge_result

        pred_post_level = judged_level if judged_level is not None else self._resolve_pred_post_level(pred)
        if pred_post_level is None:
            pred_post_level = self._map_post_choice_to_level(getattr(pred, "post_dec", None))
        gt_post_level = self._map_post_choice_to_level(gt.get("post_dec"))
        if gt_post_level is None:
            gt_post_level = self._resolve_gt_post_level(gt)
        score.post_dec, score.post_dec_detail = self._score_post_decision_simple(
            pred_post_level,
            gt_post_level,
            weight_override=default_weights["post_dec"],
        )

        return score
