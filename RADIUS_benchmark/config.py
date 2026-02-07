from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Union


@dataclass
class BenchmarkConfig:
    """Benchmark configuration.

    Notes:
    - Keep this class small and stable; it is the natural extension point for new flags.
    - Prefer adding new config fields here (with defaults) rather than scattering globals.
    """

    # API
    base_url: str = ""
    api_key: str = ""
    api_keys: List[str] = field(default_factory=list)
    judge_model_base_url: str = ""
    judge_model_api_key: str = ""
    judge_api_keys: List[str] = field(default_factory=list)
    model: str = "gpt-4o-mini"
    use_mock: bool = True

    # Action space
    vx_options: List[int] = field(default_factory=lambda: [-100, -65, -35, 0, 35, 65, 100])
    ay_options: List[int] = field(default_factory=lambda: [-300, -150, -75, -30, 0, 30, 75, 150, 225])

    # Temperatures
    temp_perception: float = 0.0
    temp_control: float = 0.0
    temp_reasoning: float = 0.6
    temp_floor: float = 0.0  # optional: if >0 and temp<=0, use this floor

    # Weights (total=100)
    score_classification: int = 15
    score_is_longtail: int = 10
    score_pre_dec: int = 15
    score_lt_ele: int = 10
    score_acc_factors: int = 15
    score_acc_effective: int = 15
    score_cot: int = 0
    score_post_dec: int = 20

    # Dataset naming
    sample_prefix: str = "dt"

    # Output
    enable_color: bool = True
    save_individual_results: bool = True
    output_dir: str = ""
    resume: bool = False

    # LLM-as-Judge
    use_llm_judge: bool = True
    judge_model: str = ""  # empty -> reuse `model`

    # Stage3 discount for Label 3/4
    stage3_discount_label3: float = 0.7
    stage3_discount_label4: float = 0.5

    # Stage3 upstream info mode(s): "blind" | "cascaded" | "oracle_gt"
    pre_decision_input: Union[str, List[str]] = "cascaded"

    # Analysis: run long-tail reasoning with is_longtail forced to True and skip instant decision
    analysis_longtail_assist: bool = False

    # API compatibility
    use_json_mode: bool = True
    enable_vision: bool = True
    vision_detail: str = "high"
    max_tokens: int = 4096

    # Execution
    workers: int = 1

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_safe_dict(self) -> Dict:
        """Config snapshot without sensitive tokens."""
        data = asdict(self)
        for key in ["api_key", "api_keys", "judge_model_api_key", "judge_api_keys"]:
            data.pop(key, None)
        return data

    @property
    def model_name_safe(self) -> str:
        safe_name = re.sub(r"[^\w\-.]", "_", self.model)
        return safe_name
