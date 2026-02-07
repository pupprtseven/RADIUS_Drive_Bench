from __future__ import annotations

import json
import time
from typing import Dict, Optional

from ..config import BenchmarkConfig
from ..logging_utils import get_logger
from ..models import LLMJudgeResult
from ..prompts import PROMPTS
from ..utils.json_utils import extract_json


class JudgeService:
    """LLM-as-Judge service."""

    def __init__(self, config: BenchmarkConfig, clients):
        self.config = config
        self.clients = clients

    def call(self, judge_type: str, format_args: Dict) -> LLMJudgeResult:
        result = LLMJudgeResult(dimension=judge_type)

        prompt_config = PROMPTS.get(f"judge_{judge_type}")
        if not prompt_config:
            result.error = f"Unknown judge type: {judge_type}"
            return result

        # Prompt formatting can raise KeyError if a required placeholder is missing.
        # Do not crash the whole pipeline; return an error so the sample can continue.
        try:
            user_prompt = prompt_config["user"].format(**format_args)
        except KeyError as e:
            result.error = f"Missing format arg for judge prompt: {e}"
            result.score = 0
            result.reasoning = ""
            return result
        result.prompt_used = user_prompt

        start = time.time()
        try:
            if self.config.use_mock:
                raw = json.dumps({"score": 8, "reasoning": "Mock evaluation - good match"})
            else:
                use_json_mode = self.config.use_json_mode
                judge_model = self.config.judge_model or self.config.model
                request_params = {
                    "model": judge_model,
                    "messages": [
                        {"role": "system", "content": prompt_config["system"]},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 200,
                }
                if use_json_mode:
                    request_params["response_format"] = {"type": "json_object"}
                client = self.clients.next_judge_client()
                if client is None:
                    raise RuntimeError("Judge client not available")
                try:
                    resp = client.chat.completions.create(**request_params)
                    raw = resp.choices[0].message.content or "{}"
                except Exception as e:
                    if "response_format" in str(e).lower() or "json" in str(e).lower():
                        get_logger().warning("JSON mode not supported for judge, retrying...")
                        request_params.pop("response_format", None)
                        resp = client.chat.completions.create(**request_params)
                        raw = resp.choices[0].message.content or "{}"
                    else:
                        raise

            result.raw_response = raw
            parsed = extract_json(raw)
            if not parsed or "score" not in parsed:
                result.error = "Failed to parse JSON from judge response"
                result.score = 0
                result.reasoning = ""
            else:
                try:
                    if "max_score" in parsed:
                        result.max_score = int(parsed.get("max_score", result.max_score))
                except Exception:
                    result.max_score = result.max_score
                upper = result.max_score or 10
                result.score = min(upper, max(0, int(parsed.get("score", 0))))
                result.reasoning = str(parsed.get("reasoning", ""))
        except Exception as e:
            result.error = str(e)
            result.score = 0

        result.latency_ms = (time.time() - start) * 1000
        return result
