from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import threading

from ..config import BenchmarkConfig
from ..constants import Stage
from ..logging_utils import get_logger
from ..models import LLMCallTrace
from ..prompts import PROMPTS
from ..utils.json_utils import extract_json
from ..utils.image_utils import ImageEncoder


class OpenAIClients:
    """Container for main and judge OpenAI clients."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.client = None  # backward compatibility
        self.judge_client = None  # backward compatibility
        self.main_clients: List = []
        self.judge_clients: List = []
        self._main_idx = 0
        self._judge_idx = 0
        self._lock = threading.Lock()
        if not config.use_mock:
            self._init_clients()

    def _init_clients(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("OpenAI package not installed. Run: pip install openai") from e

        api_keys = [k for k in self.config.api_keys if k] or ([self.config.api_key] if self.config.api_key else [])
        if not api_keys:
            raise ValueError("No API key provided. Set api_key or api_keys.")

        for key in api_keys:
            self.main_clients.append(OpenAI(base_url=self.config.base_url or None, api_key=key))
        # backward compat single client
        self.client = self.main_clients[0]

        judge_keys = [k for k in self.config.judge_api_keys if k] or (
            [self.config.judge_model_api_key] if self.config.judge_model_api_key else []
        )
        if not judge_keys:
            judge_keys = api_keys

        judge_base = self.config.judge_model_base_url or self.config.base_url
        for key in judge_keys:
            self.judge_clients.append(OpenAI(base_url=judge_base or None, api_key=key))
        self.judge_client = self.judge_clients[0]

        get_logger().success(f"OpenAI clients initialized (main={len(self.main_clients)}, judge={len(self.judge_clients)})")

    def next_main_client(self):
        if self.config.use_mock:
            return None
        with self._lock:
            client = self.main_clients[self._main_idx % len(self.main_clients)]
            self._main_idx += 1
        return client

    def next_judge_client(self):
        if self.config.use_mock:
            return None
        with self._lock:
            client = self.judge_clients[self._judge_idx % len(self.judge_clients)]
            self._judge_idx += 1
        return client


class LLMService:
    """Unified LLM caller with trace."""

    def __init__(self, config: BenchmarkConfig, clients: OpenAIClients, image_encoder: Optional[ImageEncoder] = None):
        self.config = config
        self.clients = clients
        self.image_encoder = image_encoder or ImageEncoder()

    def get_temperature(self, stage: Stage) -> float:
        if stage == Stage.CLASSIFICATION:
            temp = self.config.temp_perception
        if stage == Stage.PRE_DECISION:
            temp = self.config.temp_control
        if stage in (Stage.REASONING, Stage.LONGTAIL_CHECK):
            temp = self.config.temp_reasoning
        else:
            temp = 0.2

        if temp <= 0 and self.config.temp_floor > 0:
            return self.config.temp_floor
        return temp

    def call(self, stage: Stage, user_prompt: str, image_path: Optional[str] = None) -> LLMCallTrace:
        trace = LLMCallTrace(
            stage=stage.value,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            system_prompt=PROMPTS.get(stage.value, {}).get("system", ""),
            user_prompt=user_prompt,
            image_path=image_path or "",
            image_included=bool(image_path and os.path.exists(image_path)),
            model=self.config.model,
            temperature=self.get_temperature(stage),
            max_tokens=self.config.max_tokens,
        )

        start = time.time()
        try:
            if self.config.use_mock:
                raw = self._mock_response(stage)
            else:
                raw = self._openai_response(stage, user_prompt, image_path=image_path)
            trace.raw_response = raw
            trace.parsed_response = extract_json(raw)
            trace.parse_success = bool(trace.parsed_response)
            if not trace.parse_success:
                trace.error = trace.error or "Failed to parse JSON from model response; raw_response kept."
        except Exception as e:
            trace.error = str(e)
            trace.parse_success = False

        trace.latency_ms = (time.time() - start) * 1000
        return trace

    def _openai_response(self, stage: Stage, user_prompt: str, image_path: Optional[str] = None) -> str:
        client = self.clients.next_main_client()
        if not client:
            raise RuntimeError("OpenAI client not initialized")

        use_json_mode = self.config.use_json_mode

        system_prompt = PROMPTS.get(stage.value, {}).get("system", "")

        has_image = False
        base64_image = None
        if image_path and self.config.enable_vision:
            base64_image = self.image_encoder.encode(image_path)
            has_image = bool(base64_image)

        if has_image:
            user_content: Union[str, List[Dict]] = [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": self.config.vision_detail,
                    },
                },
            ]
        else:
            user_content = user_prompt

        request_params = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.get_temperature(stage),
            "max_tokens": self.config.max_tokens,
        }

        if use_json_mode:
            request_params["response_format"] = {"type": "json_object"}

        try:
            resp = client.chat.completions.create(**request_params)
            return resp.choices[0].message.content or "{}"
        except Exception as e:
            msg = str(e).lower()
            if "response_format" in msg or "json" in msg:
                get_logger().warning("JSON mode not supported, retrying without response_format...")
                request_params.pop("response_format", None)
                resp = client.chat.completions.create(**request_params)
                return resp.choices[0].message.content or "{}"

            if has_image and ("image" in msg or "vision" in msg or "multimodal" in msg):
                get_logger().warning("Vision not supported, retrying with text only...")
                request_params["messages"][1]["content"] = user_prompt
                resp = client.chat.completions.create(**request_params)
                return resp.choices[0].message.content or "{}"

            raise

    def _mock_response(self, stage: Stage) -> str:
        import json as _json
        from ..constants import Stage as _Stage
        mock_data = {
            _Stage.CLASSIFICATION: {
                "is_longtail": "True",
                "level1": "2",
                "level2": "2.1",
                "level3": "2.1.1",
                "lt_ele_idx": 11,
                "lt_ele_choice": "Ground obstacle",
                "lt_ele_text": "A static obstacle blocking part of the lane",
                "lt_ele": "Ground obstacle",
            },
            _Stage.PRE_DECISION: {
                "selected_vx": 0,
                "selected_ay": -150,
                "reasoning_brief": "Brake in lane to stop before the obstacle.",
            },
            _Stage.REASONING: {
                "is_longtail": "True",
                "level1": "2",
                "level2": "2.1",
                "level3": "2.1.1",
                "lt_ele_idx": 11,
                "lt_ele_choice": "Ground obstacle",
                "lt_ele_text": "A static obstacle blocking part of the lane",
                "acc_factors_multi": {
                    "group1_idx": 1,
                    "group1_choice": "Vehicles ahead",
                    "group2_idx": 2,
                    "group2_choice": "Affects own vehicle's passage",
                    "group3_idx": 2,
                    "group3_choice": "Lane-borrowing possible",
                },
                "acc_factors_text": "A static obstacle ahead blocks the current lane but adjacent lane appears clear for detour.",
                "acc_effective_indices": [2, 3],
                "COT": (
                    "1) Identify static obstacle ahead and blocked lane. "
                    "2) Confirm ego has already braked safely before the hazard. "
                    "3) Check adjacent lane availability and oncoming traffic. "
                    "4) Plan local detour via lane change when safe while keeping speed low. "
                    "5) Continue monitoring for new hazards."
                ),
                "post_decision_plan": "Wait for a safe gap, then perform a low-speed detour around the obstacle while monitoring traffic.",
                "post_decision_level": 2,
            },
            _Stage.LONGTAIL_CHECK: {
                "is_longtail": "False",
                "reason": "No rare or unusual hazards detected; normal traffic conditions.",
            },
        }
        return _json.dumps(mock_data.get(stage, {}))
