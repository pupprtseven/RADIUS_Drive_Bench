from __future__ import annotations

import re
from typing import Any


_WS_RE = re.compile(r"\s+")
_LEADING_ENUM_RE = re.compile(
    r"^\s*(?:\(?\s*)?(?:\d+|[A-Za-z]|[IVXLCDM]+)\s*[\)\.\:\-]\s*",
    re.IGNORECASE,
)
_TAX_CODE_RE = re.compile(r"(\d+(?:\.\d+){0,2})")


def parse_bool(value: Any, default: bool = False) -> bool:
    """Parse a loose boolean value with conservative fallback."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0

    text = str(value).strip().lower()
    if not text:
        return default

    if text in {"true", "1", "yes", "y", "on", "t"}:
        return True
    if text in {"false", "0", "no", "n", "off", "f"}:
        return False
    return default


def normalize_tax_code(value: Any) -> str:
    """Normalize taxonomy values into X / X.Y / X.Y.Z code format."""
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    text = text.replace("。", ".").replace("．", ".").replace(" ", "")
    m = _TAX_CODE_RE.search(text)
    if not m:
        return ""
    code = m.group(1).strip(".")
    if not code:
        return ""
    # remove zero-padded parts (e.g. 02.01.003 -> 2.1.3)
    parts = [str(int(p)) for p in code.split(".") if p != ""]
    return ".".join(parts[:3])


def normalize_choice_text(value: Any) -> str:
    """Normalize choice-like text for matching."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""

    text = text.replace("：", ":").replace("，", ",").replace("／", "/")
    text = _LEADING_ENUM_RE.sub("", text).strip()
    text = _WS_RE.sub(" ", text)
    return text

