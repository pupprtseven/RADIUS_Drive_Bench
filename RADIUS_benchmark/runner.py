from __future__ import annotations

import json
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import BenchmarkConfig
from .constants import DecisionLabel
from .logging_utils import get_logger
from .models import PipelineResult, ScoreResult, LLMJudgeResult, ActionResult
from .pipeline.benchmark import AutoDriveBenchmark
from .llm.clients import OpenAIClients
from .scoring.scorer import ScoreCalculator
from .utils.text_norm import parse_bool, normalize_tax_code


class BenchmarkRunner:
    """Batch runner."""

    def __init__(self, base_dir: str, config: Optional[BenchmarkConfig] = None):
        self.base_dir = Path(base_dir)
        self.config = config or BenchmarkConfig()
        self.clients = OpenAIClients(self.config)
        self._thread_local = threading.local()
        self.results: List[PipelineResult] = []

    def _get_benchmark(self) -> AutoDriveBenchmark:
        """Lazily create one pipeline instance per worker thread."""
        if not hasattr(self._thread_local, "benchmark"):
            self._thread_local.benchmark = AutoDriveBenchmark(self.config, clients=self.clients)
        return self._thread_local.benchmark

    @staticmethod
    def load_json_safe(path: Path) -> Dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def list_available_indices(self) -> List[int]:
        """List sample indices that have a top-level GT json file: json/{prefix}{idx}.json.

        This is useful for random sampling without requiring idx_start/idx_end.
        """
        gt_dir = self.base_dir / "json"
        if not gt_dir.exists():
            return []

        indices: List[int] = []
        for p in gt_dir.glob(f"{self.config.sample_prefix}*.json"):
            # Only files directly under json/ (exclude subdirs like pre_dec_json, gt_json)
            if not p.is_file():
                continue
            name = p.stem  # e.g., da8
            if not name.startswith(self.config.sample_prefix):
                continue
            suffix = name[len(self.config.sample_prefix):]
            if not suffix.isdigit():
                continue
            indices.append(int(suffix))

        return sorted(set(indices))

    def sample_random_by_is_longtail(
        self,
        idx_candidates: List[int],
        m_true: int,
        n_false: int,
        seed: int = 0,
        require_all_files: bool = True,
    ) -> List[int]:
        """Randomly sample m_true long-tail (gt.is_longtail==True) and n_false non-long-tail samples.

        Args:
            idx_candidates: candidate indices to sample from.
            m_true: number of long-tail samples.
            n_false: number of non-long-tail samples.
            seed: RNG seed for reproducibility.
            require_all_files: if True, only sample indices that have all required files
                               (image, pre_dec_json, gt_json, and text_gt json).
        """
        log = get_logger()
        rng = random.Random(seed)

        true_ids, false_ids = self._split_by_is_longtail(idx_candidates, require_all_files=require_all_files)

        if m_true < 0 or n_false < 0:
            raise ValueError("m_true and n_false must be >= 0")

        if m_true > len(true_ids):
            log.warning(f"Random sampling: requested m_true={m_true} but only {len(true_ids)} long-tail candidates found. Sampling all.")
            m_true = len(true_ids)
        if n_false > len(false_ids):
            log.warning(f"Random sampling: requested n_false={n_false} but only {len(false_ids)} non-long-tail candidates found. Sampling all.")
            n_false = len(false_ids)

        chosen_true = rng.sample(true_ids, k=m_true) if m_true > 0 else []
        chosen_false = rng.sample(false_ids, k=n_false) if n_false > 0 else []

        chosen = chosen_true + chosen_false
        rng.shuffle(chosen)

        log.header("Random Sampling Summary")
        log.kv("Seed", str(seed))
        log.kv("Candidates (total)", str(len(idx_candidates)))
        log.kv("Candidates (long-tail)", str(len(true_ids)))
        log.kv("Candidates (non-long-tail)", str(len(false_ids)))
        log.kv("Sampled (long-tail)", f"{len(chosen_true)}/{m_true}")
        log.kv("Sampled (non-long-tail)", f"{len(chosen_false)}/{n_false}")
        log.kv("Sampled (total)", str(len(chosen)))

        return chosen

    def filter_by_gt_is_longtail(
        self,
        idx_candidates: List[int],
        target_is_longtail: bool,
        require_all_files: bool = True,
    ) -> List[int]:
        """Filter indices by GT is_longtail flag."""
        log = get_logger()
        true_ids, false_ids = self._split_by_is_longtail(idx_candidates, require_all_files=require_all_files)
        matched = true_ids if target_is_longtail else false_ids

        log.header("GT is_longtail Filter Summary")
        log.kv("Target", str(target_is_longtail))
        log.kv("Candidates (total)", str(len(idx_candidates)))
        log.kv("Matched", str(len(matched)))
        return matched

    def _split_by_is_longtail(
        self,
        idx_candidates: List[int],
        require_all_files: bool = True,
    ) -> tuple[List[int], List[int]]:
        true_ids: List[int] = []
        false_ids: List[int] = []

        for idx in idx_candidates:
            image_file = self.base_dir / "pic" / f"{self.config.sample_prefix}{idx}.png"
            map_file = self.base_dir / "json" / "pre_dec_json" / f"{self.config.sample_prefix}{idx}_aligned.json"
            ctrl_file = self.base_dir / "json" / "gt_json" / f"{self.config.sample_prefix}{idx}_gt.json"
            gt_file = self.base_dir / "json" / f"{self.config.sample_prefix}{idx}.json"

            if require_all_files and not (image_file.exists() and map_file.exists() and ctrl_file.exists() and gt_file.exists()):
                continue

            gt = self.load_json_safe(gt_file)
            if not gt:
                continue

            v = gt.get("is_longtail", gt.get("is_longtail_gt", gt.get("longtail", gt.get("is_long_tail"))))
            s = str(v).strip().lower()
            is_lt = s in {"true", "1", "yes", "y"}

            if is_lt:
                true_ids.append(idx)
            else:
                false_ids.append(idx)

        return true_ids, false_ids

    @staticmethod
    def _parse_gt_is_longtail(gt: Dict) -> Optional[bool]:
        if not gt:
            return None
        v = gt.get("is_longtail", gt.get("is_longtail_gt", gt.get("longtail", gt.get("is_long_tail"))))
        if v is not None:
            return parse_bool(v, default=False)
        tax = normalize_tax_code(gt.get("level3", "") or gt.get("taxonomy") or gt.get("taxonomy_code") or gt.get("tax") or "")
        lt = (gt.get("lt_ele") or gt.get("lt_ele_choice") or gt.get("lt_ele_text") or "").strip()
        return bool(tax or lt)

    @staticmethod
    def _score_from_snapshot(snapshot: Dict) -> ScoreResult:
        sr = ScoreResult()
        for key in ["classification", "is_longtail", "pre_dec", "lt_ele", "acc_factors", "acc_effective", "post_dec"]:
            if key in snapshot:
                setattr(sr, key, int(snapshot.get(key, 0)))
        sr.decision_style = snapshot.get("decision_style")
        if "max_total" in snapshot:
            try:
                sr.max_total_override = int(snapshot.get("max_total"))
            except Exception:
                sr.max_total_override = sr.max_total_override
        if "post_dec_level_judge" in snapshot and isinstance(snapshot["post_dec_level_judge"], dict):
            j = snapshot["post_dec_level_judge"]
            sr.post_dec_level_judge = LLMJudgeResult(
                dimension=j.get("dimension", ""),
                score=int(j.get("score", 0)),
                max_score=int(j.get("max_score", 10)),
                reasoning=j.get("reasoning", ""),
                prompt_used=j.get("prompt_used", ""),
                raw_response=j.get("raw_response", ""),
                latency_ms=float(j.get("latency_ms", 0.0) or 0.0),
                error=j.get("error", ""),
            )
        # carry per-dimension maxima if available
        if "max_per_dim" in snapshot and isinstance(snapshot["max_per_dim"], dict):
            sr.max_per_dim = {k: int(v) for k, v in snapshot["max_per_dim"].items()}
        return sr

    @staticmethod
    def _has_stage_error(stage_snapshot: Dict) -> bool:
        if not stage_snapshot:
            return True
        status = stage_snapshot.get("status", "").strip().lower()
        if status and status not in {"completed", "done", "skipped"}:
            return True
        trace = stage_snapshot.get("llm_trace") or {}
        err = trace.get("error", "")
        return bool(err)

    def ensure_output_dir(self) -> Path:
        if self.config.output_dir:
            output_dir = Path(self.config.output_dir)
        else:
            output_dir = self.base_dir / "results" / self.config.model_name_safe
        if getattr(self.config, "analysis_longtail_assist", False):
            output_dir = output_dir / "analysis_longtail"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def run(self, idx_list: List[int]) -> List[Dict]:
        out = self.ensure_output_dir()
        self.results.clear()

        log = get_logger()
        log.header(f"Batch Execution - {len(idx_list)} samples")
        log.kv("Model", self.config.model)
        log.kv("Output Dir", str(out))
        log.kv("Workers", str(self.config.workers))

        def process_idx(idx: int) -> Optional[PipelineResult]:
            try:
                image_file = self.base_dir / "pic" / f"{self.config.sample_prefix}{idx}.png"
                map_file = self.base_dir / "json" / "pre_dec_json" / f"{self.config.sample_prefix}{idx}_aligned.json"
                ctrl_file = self.base_dir / "json" / "gt_json" / f"{self.config.sample_prefix}{idx}_gt.json"
                gt_file = self.base_dir / "json" / f"{self.config.sample_prefix}{idx}.json"

                map_json = self.load_json_safe(map_file)
                text_gt = self.load_json_safe(gt_file)
                ctrl_gt = self.load_json_safe(ctrl_file)

                if not all([map_json, text_gt, ctrl_gt]):
                    log.warning(f"Skipping {self.config.sample_prefix}{idx}: missing required files")
                    if not map_json:
                        log.warning(f"  - Missing: {map_file}")
                    if not text_gt:
                        log.warning(f"  - Missing: {gt_file}")
                    if not ctrl_gt:
                        log.warning(f"  - Missing: {ctrl_file}")
                    return None

                result_file = out / f"result_{self.config.sample_prefix}{idx}_full.json"
                if self.config.resume and result_file.exists():
                    snap = self.load_json_safe(result_file)
                    stages_snap = snap.get("stages", {}) if isinstance(snap, dict) else {}
                    has_error = (
                        self._has_stage_error(stages_snap.get("instant_decision", {}))
                        or self._has_stage_error(stages_snap.get("post_decision", {}))
                    )
                    scores_snap = snap.get("scores", {}) if isinstance(snap, dict) else {}
                    if snap and scores_snap and not has_error:
                        pr = PipelineResult(
                            data_id=idx,
                            pic_path=str(image_file),
                            pre_dec_file=str(map_file),
                            gt_json_file=str(gt_file),
                            ground_truth=snap.get("ground_truth", {}),
                        )
                        pr.scores = self._score_from_snapshot(scores_snap)
                        action_label = (snap.get("summary", {}) or {}).get("action_label")
                        if action_label is not None:
                            pr.pred_action = ActionResult(label=str(action_label))
                        self.results.append(pr)
                        log.info(f"Resume=1: skip {self.config.sample_prefix}{idx} (existing result OK)")
                        return None
                    elif snap:
                        log.info(f"Resume=1: re-running {self.config.sample_prefix}{idx} (existing result has errors/incomplete)")

                benchmark = self._get_benchmark()
                r = benchmark.run_pipeline(
                    idx=idx,
                    pic_path=str(image_file),
                    map_json=map_json,
                    text_gt_json=text_gt,
                    ctrl_gt_json=ctrl_gt,
                )

                if self.config.save_individual_results:
                    result_file = out / f"result_{self.config.sample_prefix}{idx}_full.json"
                    with open(result_file, "w", encoding="utf-8") as f:
                        json.dump(r.to_dict(), f, indent=2, ensure_ascii=False)
                return r
            except Exception as e:
                log.error(f"Pipeline failed for {self.config.sample_prefix}{idx}: {e}")
                return None

        workers = max(1, int(self.config.workers or 1))
        if workers <= 1:
            for i, idx in enumerate(idx_list):
                log.info(f"Processing {i+1}/{len(idx_list)}: {self.config.sample_prefix}{idx}")
                r = process_idx(idx)
                if r:
                    self.results.append(r)
        else:
            log.info(f"Processing in parallel with {workers} workers")
            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_map = {executor.submit(process_idx, idx): idx for idx in idx_list}
                for i, future in enumerate(as_completed(future_map), start=1):
                    idx = future_map[future]
                    try:
                        r = future.result()
                        if r:
                            self.results.append(r)
                    except Exception as e:
                        log.error(f"Pipeline failed for {self.config.sample_prefix}{idx}: {e}")
                        continue

        if self.results:
            summary_file = out / "batch_summary.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(self.get_summary_dict(), f, indent=2, ensure_ascii=False)
            get_logger().success(f"Summary saved to {summary_file}")

        self.print_batch_summary()
        return [r.to_dict() for r in self.results]

    def print_batch_summary(self) -> None:
        log = get_logger()
        if not self.results:
            log.warning("No results to summarize")
            return

        log.header("Batch Execution Summary")

        total = len(self.results)
        scores = [r.scores.total for r in self.results if r.scores]
        gt_true_scores = []
        gt_false_scores = []
        for r in self.results:
            if not r.scores:
                continue
            flag = self._parse_gt_is_longtail(getattr(r, "ground_truth", {}))
            if flag is True:
                gt_true_scores.append(r.scores.total)
            elif flag is False:
                gt_false_scores.append(r.scores.total)

        stage2_success = sum(
            1
            for r in self.results
            if r.pred_action and str(r.pred_action.label) != DecisionLabel.INVALID.value
        )
        stage2_rate = (stage2_success / total * 100) if total else 0.0

        label4_cnt = sum(
            1
            for r in self.results
            if r.pred_action and str(r.pred_action.label) == DecisionLabel.HAZARDOUS.value
        )
        label4_rate = (label4_cnt / total * 100) if total else 0.0

        log.kv("Total Samples", total)
        log.kv("Successful", len(scores))
        log.kv("Stage2 Success (Label!=0)", f"{stage2_success}/{total} ({stage2_rate:.1f}%)")
        log.kv("Label=4 (Hazardous)", f"{label4_cnt}/{total} ({label4_rate:.1f}%)")

        if scores:
            log.divider()
            log.kv("Average Score", f"{sum(scores)/len(scores):.1f}")
            log.kv("Max Score", max(scores))
            log.kv("Min Score", min(scores))
            log.kv("Std Dev", f"{self._std_dev(scores):.1f}")
            if gt_true_scores:
                log.kv("Avg Score (GT longtail=True)", f"{sum(gt_true_scores)/len(gt_true_scores):.1f} [{len(gt_true_scores)}]")
            if gt_false_scores:
                log.kv("Avg Score (GT longtail=False)", f"{sum(gt_false_scores)/len(gt_false_scores):.1f} [{len(gt_false_scores)}]")

        extra = self._compute_additional_metrics()
        if extra:
            log.divider()
            log.kv("Score Sum", f"{extra['total_score']:.1f}")
            log.kv("Samples (all/lt)", f"{extra['sample_count']}/{extra['longtail_samples']}")
            log.kv("Average", f"{extra['average_score']:.3f}")
            log.kv("PRE_DA", f"{extra['pre_da_rate']:.3f}")
            log.kv("PRE_HD", f"{extra['pre_hd_rate']:.3f}")
            log.kv("POST_DA", f"{extra['post_da_rate']:.3f}")
            log.kv("POST_HD", f"{extra['post_hd_rate']:.3f}")
            log.kv("LT_COG", f"{extra['lt_cog']:.3f}")
            log.kv("CF_ACC", f"{extra['cf_acc_rate']:.3f}")
            log.kv("CF_CDA", f"{extra['cf_cda_rate']:.3f}")
            log.kv("Guess", f"{extra['guess_rate']:.3f}")
            log.kv("RCS", f"{extra['rcs_rate']:.3f}")
            log.kv("PE", str(extra['pe_count']))
            log.kv("VE", str(extra['ve_count']))

    @staticmethod
    def _std_dev(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _compute_additional_metrics(self) -> Dict[str, Any]:
        if not self.results:
            return {}

        cfg = self.config
        total_score = 0.0
        sample_count = 0
        longtail_samples = 0

        pre_da = 0
        pre_hd = 0
        post_da = 0
        post_hd = 0

        lt_cog_sum = 0.0
        cf_acc = 0
        cf_cda = 0
        guess = 0
        rcs = 0
        pe = 0
        ve = 0

        def _max_dim(score: ScoreResult, dim: str, fallback: int) -> int:
            return score.max_per_dim.get(dim, fallback) if score else fallback

        for r in self.results:
            sc = getattr(r, "scores", None)
            if not sc:
                continue

            sample_count += 1
            total_score += sc.total
            lt_cog_sum += sc.is_longtail + sc.classification + sc.lt_ele + sc.acc_factors + sc.acc_effective

            val_res = ""
            if r.stage2_result and isinstance(r.stage2_result.validation, dict):
                val_res = str(r.stage2_result.validation.get("validation_result", "")).strip()
            if val_res in {"1", "2"}:
                pre_da += 1
            if val_res == "4":
                pre_hd += 1

            is_lt = self._parse_gt_is_longtail(getattr(r, "ground_truth", {})) is True
            if not is_lt:
                continue

            longtail_samples += 1

            gt_post = ScoreCalculator._map_post_choice_to_level(r.ground_truth.get("post_dec")) if isinstance(r.ground_truth, dict) else None
            if gt_post is None and isinstance(r.ground_truth, dict):
                gt_post = ScoreCalculator._map_post_choice_to_level(r.ground_truth.get("post_decision_plan"))

            pred_post = None
            if r.stage3_result and isinstance(r.stage3_result.outputs, dict):
                judged = r.stage3_result.outputs.get("post_decision_level_judged")
                if judged is not None:
                    try:
                        pred_post = int(judged)
                    except Exception:
                        pred_post = pred_post
            if pred_post is None and getattr(r, "post_dec_level", 0):
                pred_post = int(r.post_dec_level)
            if pred_post is None:
                pred_post = ScoreCalculator._map_post_choice_to_level(getattr(r, "post_dec", None))

            if gt_post is not None and pred_post is not None:
                if gt_post == pred_post:
                    post_da += 1
                if gt_post > pred_post:
                    post_hd += 1

            max_cls = _max_dim(sc, "classification", cfg.score_classification)
            max_islt = _max_dim(sc, "is_longtail", cfg.score_is_longtail)
            max_lt_ele = _max_dim(sc, "lt_ele", cfg.score_lt_ele)
            max_acc = _max_dim(sc, "acc_factors", cfg.score_acc_factors)
            max_acc_eff = _max_dim(sc, "acc_effective", cfg.score_acc_effective)

            post_match = bool(gt_post is not None and pred_post is not None and gt_post == pred_post)

            if sc.acc_effective >= max_acc_eff:
                cf_acc += 1
                if post_match:
                    cf_cda += 1

            perfect = (
                sc.classification >= max_cls
                and sc.is_longtail >= max_islt
                and sc.lt_ele >= max_lt_ele
                and sc.acc_factors >= max_acc
                and sc.acc_effective >= max_acc_eff
                and post_match
            )
            if perfect:
                rcs += 1
            elif post_match:
                guess += 1

            if post_match and (sc.lt_ele < max_lt_ele or sc.acc_factors < max_acc):
                pe += 1
            if post_match and sc.acc_effective < max_acc_eff:
                ve += 1

        if sample_count == 0:
            return {}

        lt_den = max(1, longtail_samples)

        return {
            "total_score": total_score,
            "sample_count": sample_count,
            "longtail_samples": longtail_samples,
            "average_score": total_score / sample_count if sample_count else 0.0,
            "pre_da_rate": pre_da / sample_count,
            "pre_hd_rate": pre_hd / sample_count,
            "post_da_rate": post_da / lt_den,
            "post_hd_rate": post_hd / lt_den,
            "lt_cog": lt_cog_sum / sample_count if sample_count else 0.0,
            "cf_acc_rate": cf_acc / lt_den,
            "cf_cda_rate": cf_cda / lt_den,
            "guess_rate": guess / lt_den,
            "rcs_rate": rcs / lt_den,
            "pe_count": pe,
            "ve_count": ve,
        }

    def get_summary_dict(self) -> Dict:
        if not self.results:
            return {"error": "No results available"}

        scores = [r.scores.total for r in self.results if r.scores]
        valid_results = [r for r in self.results if r.scores]
        gt_true_scores = [
            r.scores.total for r in valid_results if self._parse_gt_is_longtail(getattr(r, "ground_truth", {})) is True
        ]
        gt_false_scores = [
            r.scores.total for r in valid_results if self._parse_gt_is_longtail(getattr(r, "ground_truth", {})) is False
        ]

        def avg(vals: List[float]) -> float:
            return round(sum(vals) / len(vals), 2) if vals else 0.0

        return {
            "total_samples": len(self.results),
            "successful_samples": len(scores),
            "statistics": {
                "avg_score": avg(scores),
                "max_score": max(scores) if scores else 0,
                "min_score": min(scores) if scores else 0,
                "std_dev": round(self._std_dev(scores), 2) if scores else 0,
                "avg_score_gt_true": avg(gt_true_scores),
                "avg_score_gt_false": avg(gt_false_scores),
                "count_gt_true": len(gt_true_scores),
                "count_gt_false": len(gt_false_scores),
            },
            "dimension_averages": {
                "classification": avg([r.scores.classification for r in valid_results]),
                "is_longtail": avg([r.scores.is_longtail for r in valid_results]),
                "pre_dec": avg([r.scores.pre_dec for r in valid_results]),
                "lt_ele": avg([r.scores.lt_ele for r in valid_results]),
                "acc_factors": avg([r.scores.acc_factors for r in valid_results]),
                "acc_effective": avg([r.scores.acc_effective for r in valid_results]),
                "post_dec": avg([r.scores.post_dec for r in valid_results]),
                "safety_score": avg([r.scores.pre_dec + r.scores.post_dec for r in valid_results]),
                "lt_cog": avg([r.scores.is_longtail + r.scores.classification + r.scores.lt_ele + r.scores.acc_factors + r.scores.acc_effective for r in valid_results]),
                "lt_comp": avg([r.scores.lt_ele + r.scores.acc_factors + r.scores.acc_effective + r.scores.post_dec for r in valid_results]),
            },
            "metrics": self._compute_additional_metrics(),
            "results_summary": [r.to_summary_dict() for r in self.results],
        }
