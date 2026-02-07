from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .constants import DecisionLabel, Stage


@dataclass
class LLMJudgeResult:
    dimension: str = ""
    score: int = 0
    max_score: int = 10
    reasoning: str = ""
    prompt_used: str = ""
    raw_response: str = ""
    latency_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LLMCallTrace:
    stage: str
    timestamp: str = ""
    system_prompt: str = ""
    user_prompt: str = ""
    image_included: bool = False
    image_path: str = ""
    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096
    raw_response: str = ""
    parsed_response: Dict = field(default_factory=dict)
    parse_success: bool = False
    latency_ms: float = 0.0
    token_count_estimate: int = 0
    error: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ActionResult:
    vx: int = 0
    ay: int = 0
    label: str = '0'
    label_description: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ScoreResult:
    classification: int = 0
    is_longtail: int = 0
    pre_dec: int = 0
    lt_ele: int = 0
    acc_factors: int = 0
    acc_effective: int = 0
    post_dec: int = 0

    classification_detail: str = ""
    is_longtail_detail: str = ""
    pre_dec_detail: str = ""
    lt_ele_detail: str = ""
    acc_factors_detail: str = ""
    acc_effective_detail: str = ""
    post_dec_detail: str = ""

    post_dec_level_judge: Optional[LLMJudgeResult] = None

    safety_score: Optional[int] = None
    lt_cog: Optional[int] = None
    lt_comp: Optional[int] = None
    decision_style: Optional[int] = None
    max_total_override: Optional[int] = None
    max_per_dim: Dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return (
            self.classification
            + self.is_longtail
            + self.pre_dec
            + self.lt_ele
            + self.acc_factors
            + self.acc_effective
            + self.post_dec
        )

    @property
    def max_total(self) -> int:
        return self.max_total_override or 100

    def _compute_composites(self) -> None:
        self.safety_score = self.pre_dec + self.post_dec
        self.lt_cog = self.is_longtail + self.classification + self.lt_ele + self.acc_factors + self.acc_effective
        self.lt_comp = self.lt_ele + self.acc_factors + self.acc_effective + self.post_dec

    def to_dict(self) -> Dict:
        self._compute_composites()
        result = {
            "classification": self.classification,
            "classification_detail": self.classification_detail,
            "is_longtail": self.is_longtail,
            "is_longtail_detail": self.is_longtail_detail,
            "pre_dec": self.pre_dec,
            "pre_dec_detail": self.pre_dec_detail,
            "lt_ele": self.lt_ele,
            "lt_ele_detail": self.lt_ele_detail,
            "acc_factors": self.acc_factors,
            "acc_factors_detail": self.acc_factors_detail,
            "acc_effective": self.acc_effective,
            "acc_effective_detail": self.acc_effective_detail,
            "post_dec": self.post_dec,
            "post_dec_detail": self.post_dec_detail,
            "total": self.total,
            "max_total": self.max_total,
            "percentage": round(self.total / self.max_total * 100, 1) if self.max_total else 0.0,
            "safety_score": self.safety_score,
            "lt_cog": self.lt_cog,
            "lt_comp": self.lt_comp,
            "decision_style": self.decision_style,
            "max_per_dim": self.max_per_dim,
        }
        if self.post_dec_level_judge:
            result["post_dec_level_judge"] = self.post_dec_level_judge.to_dict()
        return result


@dataclass
class StageResult:
    stage: str
    status: str = "pending"
    inputs: Dict = field(default_factory=dict)
    llm_trace: Optional[LLMCallTrace] = None
    outputs: Dict = field(default_factory=dict)
    validation: Dict = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict:
        result = {
            "stage": self.stage,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "duration_ms": self.duration_ms,
        }
        if self.llm_trace:
            result["llm_trace"] = self.llm_trace.to_dict()
        if self.validation:
            result["validation"] = self.validation
        return result


@dataclass
class PipelineResult:
    data_id: int = 0
    pic_name: str = ""
    pic_path: str = ""
    pre_dec_file: str = ""
    gt_json_file: str = ""

    run_timestamp: str = ""
    total_duration_ms: float = 0.0
    config_snapshot: Dict = field(default_factory=dict)

    stage1_result: Optional[StageResult] = None
    stage2_result: Optional[StageResult] = None
    stage3_result: Optional[StageResult] = None

    is_longtail: str = "False"
    level1: str = "N/A"
    level2: str = "N/A"
    level3: str = "N/A"
    lt_ele: str = "N/A"
    lt_ele_idx: int = -1
    lt_ele_text: str = ""

    pred_action: Optional[ActionResult] = None

    acc_factors: str = "N/A"
    acc_factors_multi: Dict[str, Any] = field(default_factory=dict)
    acc_factors_effective: List[int] = field(default_factory=list)
    COT: str = "N/A"
    post_dec: str = "N/A"
    post_dec_level: int = 0
    post_dec_level_model: int = 0
    post_dec_style: str = "N/A"
    post_policy: str = "N/A"
    safe_distance_level: int = 0

    scores: Optional[ScoreResult] = None
    ground_truth: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "meta": {
                "data_id": self.data_id,
                "pic_name": self.pic_name,
                "pic_path": self.pic_path,
                "pre_dec_file": self.pre_dec_file,
                "gt_json_file": self.gt_json_file,
                "run_timestamp": self.run_timestamp,
                "total_duration_ms": self.total_duration_ms,
            },
            "config": self.config_snapshot,
            "stages": {
                "instant_decision": self.stage2_result.to_dict() if self.stage2_result else None,
                "post_decision": self.stage3_result.to_dict() if self.stage3_result else None,
            },
            "summary": {
                "classification": {
                    "is_longtail": self.is_longtail,
                    "level1": self.level1,
                    "level2": self.level2,
                    "level3": self.level3,
                    "lt_ele": self.lt_ele,
                    "lt_ele_idx": self.lt_ele_idx,
                    "lt_ele_text": self.lt_ele_text,
                    "acc_factors_effective": self.acc_factors_effective or None,
                },
                "action": self.pred_action.to_dict() if self.pred_action else None,
                "post_dec_style": self.post_dec_style,
            },
            "scores": self.scores.to_dict() if self.scores else None,
            "ground_truth": self.ground_truth,
        }

    def to_summary_dict(self) -> Dict:
        return {
            "data_id": self.data_id,
            "is_longtail": self.is_longtail,
            "level3": self.level3,
            "action": f"vx={self.pred_action.vx}, ay={self.pred_action.ay}" if self.pred_action else "N/A",
            "action_label": self.pred_action.label if self.pred_action else "N/A",
            "post_dec": self.post_dec,
            "post_dec_level": self.post_dec_level,
            "post_dec_style": self.post_dec_style,
            "total_score": self.scores.total if self.scores else 0,
            "duration_ms": round(self.total_duration_ms, 1),
        }
