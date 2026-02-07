from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..config import BenchmarkConfig
from ..constants import (
    ACC_FACTORS_GROUPS,
    DecisionLabel,
    LT_ELE_CHOICES,
    POST_DEC_TO_LEVEL,
    POST_DEC_TO_POLICY,
    Stage,
    TAXONOMY_TEXT,
)
from ..logging_utils import get_logger, set_logger
from ..models import ActionResult, PipelineResult, StageResult
from ..prompts import PROMPTS
from ..utils.choice_resolvers import (
    format_acc_factors_choices,
    format_lt_ele_choices,
    resolve_lt_ele_choice,
)
from ..utils.map_prompt import parse_map_to_prompt
from ..llm.clients import OpenAIClients, LLMService
from ..llm.judge import JudgeService
from ..scoring.scorer import ScoreCalculator


class AutoDriveBenchmark:
    """Perception + instant decision + post-stop decision pipeline."""

    def __init__(self, config: Optional[BenchmarkConfig] = None, clients: Optional[OpenAIClients] = None):
        self.config = config or BenchmarkConfig()

        # initialize logger singleton
        set_logger(enable_color=self.config.enable_color, name="AutoDriveBenchmark")
        self.log = get_logger()

        # LLM services
        self.clients = clients or OpenAIClients(self.config)
        self.llm = LLMService(self.config, self.clients)
        self.judge = JudgeService(self.config, self.clients)

        # Scoring
        self.scorer = ScoreCalculator(self.config, judge=self.judge if self.config.use_llm_judge else None)

    # -------- Pipeline helpers --------
    @staticmethod
    def is_truthy(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)

    @staticmethod
    def _get_block_reason(label: DecisionLabel) -> str:
        reasons = {
            DecisionLabel.INVALID: "Invalid action or collision detected",
            DecisionLabel.RISKY: "Action classified as risky (Label 3)",
            DecisionLabel.HAZARDOUS: "Action classified as hazardous (Label 4)",
        }
        return reasons.get(label, "Pre-decision did not pass safety check")

    @staticmethod
    def _acc_text_from_multi(acc_multi: Dict[str, Any]) -> str:
        if not isinstance(acc_multi, dict) or not acc_multi:
            return ""
        parts = []
        for tag, key in (("G1", "group1_choice"), ("G2", "group2_choice"), ("G3", "group3_choice")):
            val = str(acc_multi.get(key, "") or "").strip()
            if val:
                parts.append(f"{tag}={val}")
        return "; ".join(parts)

    def _populate_stage3_outputs(
        self,
        res_3: Dict[str, Any],
        stage3_result: StageResult,
        result: PipelineResult,
        force_is_longtail: bool = False,
        mode: str = "standard",
    ) -> None:
        if not isinstance(res_3, dict):
            res_3 = {}
        raw_is_longtail = str(res_3.get("is_longtail", "False"))
        result.is_longtail = "True" if force_is_longtail else raw_is_longtail
        result.level1 = str(res_3.get("level1", "N/A"))
        result.level2 = str(res_3.get("level2", "N/A"))
        result.level3 = str(res_3.get("level3", "N/A"))

        lt_idx_raw = res_3.get("lt_ele_idx", -1)
        try:
            lt_idx = int(lt_idx_raw)
        except (TypeError, ValueError):
            lt_idx = -1

        lt_choice_raw = (res_3.get("lt_ele_choice") or res_3.get("lt_ele") or "").strip()
        lt_choice = "N/A"
        lt_choice_reason = "missing"
        if lt_choice_raw:
            lt_choice_canon, idx_from_choice, lt_choice_reason = resolve_lt_ele_choice(lt_choice_raw, allow_fuzzy=True)
            if idx_from_choice >= 0:
                lt_choice = lt_choice_canon
                lt_idx = idx_from_choice
            elif 0 <= lt_idx < len(LT_ELE_CHOICES):
                lt_choice = LT_ELE_CHOICES[lt_idx]
                lt_choice_reason = f"idx_fallback_due_to_unresolved_choice({lt_choice_reason})"
            else:
                lt_choice = lt_choice_canon or lt_choice_raw
        elif 0 <= lt_idx < len(LT_ELE_CHOICES):
            lt_choice = LT_ELE_CHOICES[lt_idx]
            lt_choice_reason = "idx_field"

        lt_text = res_3.get("lt_ele_text", "")
        result.lt_ele = str(lt_choice)
        result.lt_ele_idx = lt_idx
        result.lt_ele_text = lt_text

        acc_multi = res_3.get("acc_factors_multi", {}) or {}
        acc_text = res_3.get("acc_factors_text", "")
        if not isinstance(acc_multi, dict):
            acc_multi = {}
        if not acc_text:
            acc_text = self._acc_text_from_multi(acc_multi)
        result.acc_factors_multi = acc_multi
        result.acc_factors = str(acc_text or "")

        eff_set = self.scorer._normalize_effective_prediction(res_3.get("acc_effective_indices", []))
        result.acc_factors_effective = sorted(eff_set)
        eff_notes = res_3.get("acc_effective_notes", {})
        if not isinstance(eff_notes, dict):
            eff_notes = {}

        result.COT = str(res_3.get("COT", "N/A"))
        result.post_dec = str(res_3.get("post_decision_plan", res_3.get("post_dec", "N/A")))
        result.post_dec_style = str(res_3.get("post_decision_style", "N/A"))

        level_guess = 0
        result.post_dec_level_model = level_guess
        result.post_dec_level = level_guess
        result.post_policy = "N/A"

        stage3_result.outputs = {
            "mode": mode,
            "is_longtail": result.is_longtail,
            "level1": result.level1,
            "level2": result.level2,
            "level3": result.level3,
            "lt_ele_idx": lt_idx,
            "lt_ele_choice": lt_choice,
            "lt_ele_choice_parse_reason": lt_choice_reason,
            "lt_ele_text": lt_text,
            "acc_factors_multi": acc_multi,
            "acc_factors_text": result.acc_factors,
            "acc_effective_indices": result.acc_factors_effective,
            "acc_effective_notes": eff_notes,
            "COT": result.COT,
            "post_decision_plan": result.post_dec,
            "post_decision_style": result.post_dec_style,
        }
        if force_is_longtail:
            stage3_result.outputs["is_longtail_forced"] = True
            stage3_result.outputs["is_longtail_raw"] = raw_is_longtail

    # -------- Main entry --------
    def run_pipeline(
        self,
        idx: int,
        pic_path: str,
        map_json: Dict,
        text_gt_json: Dict,
        ctrl_gt_json: Dict,
    ) -> PipelineResult:
        pipeline_start = time.time()

        result = PipelineResult(
            data_id=idx,
            pic_name=f"{self.config.sample_prefix}{idx}",
            pic_path=pic_path,
            pre_dec_file=f"pre_dec_json/{self.config.sample_prefix}{idx}_aligned.json",
            gt_json_file=f"gt_json/{self.config.sample_prefix}{idx}_gt.json",
            run_timestamp=datetime.now().isoformat(),
            config_snapshot=self.config.to_safe_dict(),
            ground_truth=text_gt_json.copy(),
        )

        analysis_longtail_mode = bool(getattr(self.config, "analysis_longtail_assist", False))

        self.log.header(f"Pipeline Execution - Data ID: {idx}")
        self.log.kv("Image", pic_path)
        self.log.kv("Model", self.config.model)
        self.log.kv("Mode", "Mock" if self.config.use_mock else "Live API")

        map_desc = parse_map_to_prompt(map_json)

        # ---------------- Stage 1 ----------------
        self.log.section("Instant Decision-Making")
        stage2_start = time.time()
        stage2_result = StageResult(stage="instant_decision")
        pred_vx, pred_ay = 0, 0

        if analysis_longtail_mode:
            self.log.stage(1, "Instant Decision-Making", "SKIP")

            gt_opt_control = self.scorer.get_optimal_control_from_valid_controls(ctrl_gt_json.get("valid_controls", []))
            if gt_opt_control is not None:
                pred_vx, pred_ay = gt_opt_control
                action_reason = "GT optimal control injected for analysis"
            else:
                pred_vx, pred_ay = 0, 0
                action_reason = "GT optimal control unavailable; fallback to (0,0)"

            decision_label = DecisionLabel.OPTIMAL
            stage2_result.inputs = {
                "map_entities_count": len(map_json.get("entities", [])),
                "vx_options": self.config.vx_options,
                "ay_options": self.config.ay_options,
                "mode": "analysis_longtail_assist",
            }
            stage2_result.outputs = {
                "mode": "analysis_longtail_assist",
                "selected_vx": pred_vx,
                "selected_ay": pred_ay,
                "reasoning_brief": action_reason,
                "decision_label": decision_label.value,
            }
            stage2_result.status = "skipped"
            stage2_result.duration_ms = (time.time() - stage2_start) * 1000
            result.stage2_result = stage2_result

            result.pred_action = ActionResult(
                vx=int(pred_vx),
                ay=int(pred_ay),
                label=decision_label.value,
                label_description=decision_label.description,
            )

            self.log.kv("Action", f"vx={pred_vx}, ay={pred_ay}")
            self.log.kv("Reasoning", action_reason)
            self.log.kv("Validation", f"Label {decision_label.value} ({decision_label.description})")
        else:
            self.log.stage(1, "Instant Decision-Making", "START")

            user_prompt_2 = PROMPTS["stage2"]["user"].format(
                map_description=map_desc,
                vx_options=self.config.vx_options,
                ay_options=self.config.ay_options,
            )
            stage2_result.inputs = {
                "map_entities_count": len(map_json.get("entities", [])),
                "vx_options": self.config.vx_options,
                "ay_options": self.config.ay_options,
            }

            trace_2 = self.llm.call(Stage.PRE_DECISION, user_prompt_2, pic_path)
            stage2_result.llm_trace = trace_2
            res_2 = trace_2.parsed_response

            pred_vx = res_2.get("selected_vx", 0)
            pred_ay = res_2.get("selected_ay", 0)
            reasoning = res_2.get("reasoning_brief", "")

            valid_list = ctrl_gt_json.get("valid_controls", [])
            decision_label = self.scorer.validate_pre_decision(pred_vx, pred_ay, valid_list)

            stage2_result.validation = {
                "valid_controls_count": len(valid_list),
                "selected_action": {"vx": pred_vx, "ay": pred_ay},
                "validation_result": decision_label.value,
                "validation_description": decision_label.description,
            }

            result.pred_action = ActionResult(
                vx=int(pred_vx) if pred_vx is not None else 0,
                ay=int(pred_ay) if pred_ay is not None else 0,
                label=decision_label.value,
                label_description=decision_label.description,
            )

            stage2_result.outputs = {
                "selected_vx": pred_vx,
                "selected_ay": pred_ay,
                "reasoning_brief": reasoning,
                "decision_label": decision_label.value,
            }
            stage2_result.status = "completed"
            stage2_result.duration_ms = (time.time() - stage2_start) * 1000
            result.stage2_result = stage2_result

            self.log.kv("Action", f"vx={pred_vx}, ay={pred_ay}")
            self.log.kv("Reasoning", reasoning[:80] + "..." if len(reasoning) > 80 else reasoning)
            self.log.kv("Validation", f"Label {decision_label.value} ({decision_label.description})")
            self.log.kv("Latency", f"{trace_2.latency_ms:.1f}ms")
            self.log.stage(1, "Instant Decision-Making", "DONE")

        # ---------------- Stage 2 ----------------
        self.log.section("Stage 2: E2E Perception + Post Decision")
        stage3_start = time.time()
        stage3_result = StageResult(stage="post_decision")

        gt_has_is_longtail = isinstance(text_gt_json, dict) and ("is_longtail" in text_gt_json)
        gt_is_longtail = self.is_truthy(text_gt_json.get("is_longtail")) if gt_has_is_longtail else True
        is_longtail_only_mode = bool(gt_has_is_longtail and (not gt_is_longtail))
        if analysis_longtail_mode and gt_has_is_longtail and not gt_is_longtail:
            self.log.warning("analysis_longtail_assist enabled but GT is_longtail=False; forcing long-tail analysis anyway.")

        stage3_vx, stage3_ay = pred_vx, pred_ay
        stage3_action_source = "pred"
        if analysis_longtail_mode:
            stage3_action_source = "analysis_gt_optimal" if (pred_vx or pred_ay) else "analysis_fallback"
        elif decision_label in (DecisionLabel.RISKY, DecisionLabel.HAZARDOUS):
            gt_opt = self.scorer.get_optimal_control_from_valid_controls(ctrl_gt_json.get("valid_controls", []))
            if gt_opt is not None:
                stage3_vx, stage3_ay = gt_opt
                stage3_action_source = "gt_label1_injected"
            else:
                stage3_action_source = "gt_label1_missing_use_pred"

        result.ground_truth["stage3_action_source"] = stage3_action_source
        result.ground_truth["stage3_action_used"] = {"vx": stage3_vx, "ay": stage3_ay}

        ego_vx_cm_s = 0.0
        ego_vy_cm_s = 0.0
        try:
            entities = (map_json or {}).get("entities", [])
            ego = next((e for e in entities if e.get("type") == "ego"), None)
            if ego:
                ego_vx_cm_s = float(ego.get("vx", 0) or 0)
                ego_vy_cm_s = float(ego.get("vy", 0) or 0)
        except Exception:
            pass

        if abs(ego_vy_cm_s) <= 5:
            current_state = "STOPPED_NEAR_HAZARD"
        elif stage3_ay <= -75:
            current_state = "BRAKING_HARD_NEAR_HAZARD"
        elif abs(stage3_vx) > 0:
            current_state = "LATERAL_MANEUVER_NEAR_HAZARD"
        else:
            current_state = "MOVING_NEAR_HAZARD"

        if is_longtail_only_mode:
            self.log.stage(2, "Post Decision (GT=False is_longtail check)", "START")

            user_prompt_lt_only = PROMPTS["stage3_is_longtail_only"]["user"].format(
                sup_description=str(text_gt_json.get("Sup_description", "N/A")),
                map_description=map_desc,
                taxonomy=TAXONOMY_TEXT,
                lt_ele_choices=format_lt_ele_choices(),
            )

            stage3_result.inputs = {
                "action_taken": {"vx": stage3_vx, "ay": stage3_ay},
                "action_source": stage3_action_source,
                "current_state": current_state,
                "map_entities_count": len(map_json.get("entities", [])),
                "mode": "is_longtail_only",
            }

            trace_lt = self.llm.call(Stage.LONGTAIL_CHECK, user_prompt_lt_only, pic_path)
            stage3_result.llm_trace = trace_lt
            res_lt = trace_lt.parsed_response

            result.is_longtail = str(res_lt.get("is_longtail", "False"))
            lt_reason = str(res_lt.get("reason") or res_lt.get("reason_brief") or "")
            result.COT = lt_reason or result.COT

            stage3_result.outputs = {
                "mode": "is_longtail_only",
                "decision_label": decision_label.value,
                "is_longtail": result.is_longtail,
                "reason": lt_reason,
            }
            stage3_result.status = "completed"
            stage3_result.duration_ms = (time.time() - stage3_start) * 1000

            self.log.kv("E2E is_longtail", result.is_longtail)
            self.log.kv("Latency", f"{trace_lt.latency_ms:.1f}ms")
            self.log.stage(2, "Post Decision (GT=False is_longtail check)", "DONE")

        elif analysis_longtail_mode:
            self.log.stage(2, "Post Decision (Long-tail Assist)", "START")

            user_prompt_3_assist = PROMPTS["stage3_longtail_assist"]["user"].format(
                sup_description=str(text_gt_json.get("Sup_description", "N/A")),
                map_description=map_desc,
                taxonomy=TAXONOMY_TEXT,
                lt_ele_choices=format_lt_ele_choices(),
                acc_factors_choices=format_acc_factors_choices(ACC_FACTORS_GROUPS),
                vx=stage3_vx,
                ay=stage3_ay,
                current_state=current_state,
            )

            stage3_result.inputs = {
                "action_taken": {"vx": stage3_vx, "ay": stage3_ay},
                "action_source": stage3_action_source,
                "current_state": current_state,
                "map_entities_count": len(map_json.get("entities", [])),
                "mode": "analysis_longtail_assist",
            }

            trace_3 = self.llm.call(Stage.REASONING, user_prompt_3_assist, pic_path)
            stage3_result.llm_trace = trace_3
            res_3 = trace_3.parsed_response

            self._populate_stage3_outputs(res_3, stage3_result, result, force_is_longtail=True, mode="analysis_longtail_assist")
            stage3_result.status = "completed"
            stage3_result.duration_ms = (time.time() - stage3_start) * 1000

            self.log.kv("E2E is_longtail", result.is_longtail)
            self.log.kv("E2E Classification", f"{result.level1} → {result.level2} → {result.level3}")
            self.log.kv("E2E Long-tail Element", result.lt_ele)
            acc_preview = result.acc_factors[:80] + "..." if len(result.acc_factors) > 80 else result.acc_factors
            self.log.kv("E2E ACC Factors", acc_preview or "N/A")
            self.log.kv("Effective Factors", result.acc_factors_effective)
            self.log.kv("Post Decision Plan", result.post_dec)
            self.log.kv("Post Decision Level (model)", result.post_dec_level_model)
            self.log.kv("Latency", f"{trace_3.latency_ms:.1f}ms")
            self.log.stage(2, "Post Decision (Long-tail Assist)", "DONE")

        elif decision_label != DecisionLabel.INVALID:
            self.log.stage(2, "Post Decision", "START")

            user_prompt_3 = PROMPTS["stage3"]["user"].format(
                sup_description=str(text_gt_json.get("Sup_description", "N/A")),
                map_description=map_desc,
                taxonomy=TAXONOMY_TEXT,
                lt_ele_choices=format_lt_ele_choices(),
                acc_factors_choices=format_acc_factors_choices(ACC_FACTORS_GROUPS),
                vx=stage3_vx,
                ay=stage3_ay,
                decision_label=decision_label.value,
                decision_label_desc=decision_label.description,
                current_state=current_state,
            )

            stage3_result.inputs = {
                "action_taken": {"vx": stage3_vx, "ay": stage3_ay},
                "action_source": stage3_action_source,
                "current_state": current_state,
                "map_entities_count": len(map_json.get("entities", [])),
                "mode": "standard",
            }

            trace_3 = self.llm.call(Stage.REASONING, user_prompt_3, pic_path)
            stage3_result.llm_trace = trace_3
            res_3 = trace_3.parsed_response
            self._populate_stage3_outputs(res_3, stage3_result, result, force_is_longtail=False, mode="standard")
            stage3_result.status = "completed"
            stage3_result.duration_ms = (time.time() - stage3_start) * 1000

            self.log.kv("E2E is_longtail", result.is_longtail)
            self.log.kv("E2E Classification", f"{result.level1} → {result.level2} → {result.level3}")
            self.log.kv("E2E Long-tail Element", result.lt_ele)
            acc_preview = result.acc_factors[:80] + "..." if len(result.acc_factors) > 80 else result.acc_factors
            self.log.kv("E2E ACC Factors", acc_preview or "N/A")
            self.log.kv("Effective Factors", result.acc_factors_effective)
            self.log.kv("Post Decision Plan", result.post_dec)
            self.log.kv("Post Decision Level (model)", result.post_dec_level_model)
            self.log.kv("Latency", f"{trace_3.latency_ms:.1f}ms")
            self.log.stage(2, "Post Decision", "DONE")

        else:
            block_reason = self._get_block_reason(decision_label)
            result.COT = f"Simulation Terminated: {block_reason}"
            result.post_dec = "Emergency Termination"
            stage3_result.status = "blocked"
            stage3_result.outputs = {
                "block_reason": block_reason,
                "decision_label": decision_label.value,
                "COT": result.COT,
                "post_dec": result.post_dec,
            }
            self.log.stage(2, "Post Decision", "BLOCK")
            self.log.warning(f"Blocked: {block_reason}")

        stage3_total_ms = (time.time() - stage3_start) * 1000
        stage3_result.outputs = stage3_result.outputs or {}
        if stage3_result.status in ("skipped", "blocked"):
            stage3_result.duration_ms = stage3_total_ms
        result.stage3_result = stage3_result

        # ---------------- Scoring ----------------
        self.log.section("Scoring")
        result.scores = self.scorer.calculate_score(result, text_gt_json, decision_label)
        if result.scores and result.scores.post_dec_level_judge:
            judged_lvl = result.scores.post_dec_level_judge.score
            if judged_lvl:
                try:
                    result.post_dec_level = int(judged_lvl)
                except Exception:
                    result.post_dec_level = result.post_dec_level
                if result.stage3_result is not None:
                    result.stage3_result.outputs = result.stage3_result.outputs or {}
                    result.stage3_result.outputs["post_decision_level_judged"] = judged_lvl
                self.log.kv("Post Decision Level (judged)", judged_lvl)

        max_per_dim = getattr(result.scores, "max_per_dim", {}) if result.scores else {}
        self.log.score_bar("classification", result.scores.classification, max_per_dim.get("classification", self.config.score_classification))
        self.log.score_bar("is_longtail", result.scores.is_longtail, max_per_dim.get("is_longtail", self.config.score_is_longtail))
        self.log.score_bar("pre_dec", result.scores.pre_dec, max_per_dim.get("pre_dec", self.config.score_pre_dec))
        self.log.score_bar("lt_ele", result.scores.lt_ele, max_per_dim.get("lt_ele", self.config.score_lt_ele))
        self.log.score_bar("acc_factors", result.scores.acc_factors, max_per_dim.get("acc_factors", self.config.score_acc_factors))
        self.log.score_bar("acc_effective", result.scores.acc_effective, max_per_dim.get("acc_effective", self.config.score_acc_effective))
        self.log.score_bar("post_dec", result.scores.post_dec, max_per_dim.get("post_dec", self.config.score_post_dec))
        self.log.divider()
        self.log.score_bar("TOTAL", result.scores.total, result.scores.max_total)

        result.total_duration_ms = (time.time() - pipeline_start) * 1000

        self.log.section("Summary")
        self.log.kv("Total Duration", f"{result.total_duration_ms:.1f}ms")
        final_pct = result.scores.to_dict().get("percentage", 0.0) if result.scores else 0.0
        self.log.kv("Final Score", f"{result.scores.total}/100 ({final_pct}%)")
        return result
