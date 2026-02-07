from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, Optional


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _try_parse_dict(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None

    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    try:
        obj = ast.literal_eval(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    return None


def _extract_brace_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start < 0:
        return None

    depth = 0
    in_str = False
    esc = False
    quote = ""
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
            continue

        if ch in {"'", '"'}:
            in_str = True
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(raw: Any) -> Dict[str, Any]:
    """Best-effort JSON object extraction from LLM response text."""
    if isinstance(raw, dict):
        return raw
    if raw is None:
        return {}

    text = str(raw).strip()
    if not text:
        return {}

    direct = _try_parse_dict(text)
    if direct is not None:
        return direct

    for m in _FENCE_RE.finditer(text):
        parsed = _try_parse_dict(m.group(1))
        if parsed is not None:
            return parsed

    candidate = _extract_brace_object(text)
    if candidate:
        parsed = _try_parse_dict(candidate)
        if parsed is not None:
            return parsed

    return {}

