from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable, List, Tuple

from ..constants import LT_ELE_CHOICES, POST_DEC_CHOICES
from .text_norm import normalize_choice_text


def format_lt_ele_choices() -> str:
    return "\n".join([f"{i}. {c}" for i, c in enumerate(LT_ELE_CHOICES)])


def format_acc_factors_choices(groups: Iterable[Iterable[str]]) -> str:
    lines: List[str] = []
    for g_idx, group in enumerate(groups, start=1):
        lines.append(f"Group {g_idx}:")
        for c_idx, choice in enumerate(group, start=1):
            lines.append(f"  {c_idx}. {choice}")
    return "\n".join(lines)


def _best_fuzzy_match(raw: str, choices: List[str]) -> Tuple[str, int, float]:
    if not raw:
        return "", -1, 0.0

    norm_raw = normalize_choice_text(raw).lower()
    best_idx = -1
    best_choice = ""
    best_score = 0.0
    for idx, c in enumerate(choices):
        norm_c = normalize_choice_text(c).lower()
        if not norm_c:
            continue
        if norm_raw == norm_c:
            return c, idx, 1.0
        if norm_raw in norm_c or norm_c in norm_raw:
            score = 0.95
        else:
            score = SequenceMatcher(None, norm_raw, norm_c).ratio()
        if score > best_score:
            best_score = score
            best_idx = idx
            best_choice = c
    return best_choice, best_idx, best_score


def _parse_numeric_choice(raw: str, choices: List[str]) -> Tuple[str, int, str]:
    text = (raw or "").strip()
    if not text:
        return "", -1, "empty"

    m = re.match(r"^\s*(-?\d+)\s*$", text)
    if m:
        num = int(m.group(1))
        if 0 <= num < len(choices):
            return choices[num], num, "numeric_0_based"
        if 1 <= num <= len(choices):
            idx = num - 1
            return choices[idx], idx, "numeric_1_based"

    m = re.match(r"^\s*(-?\d+)\s*[\)\.\:\-]\s*", text)
    if m:
        num = int(m.group(1))
        if 0 <= num < len(choices):
            return choices[num], num, "prefixed_numeric_0_based"
        if 1 <= num <= len(choices):
            idx = num - 1
            return choices[idx], idx, "prefixed_numeric_1_based"

    return "", -1, "not_numeric"


def resolve_lt_ele_choice(raw_choice: str, allow_fuzzy: bool = True) -> Tuple[str, int, str]:
    parsed_choice, parsed_idx, reason = _parse_numeric_choice(raw_choice, LT_ELE_CHOICES)
    if parsed_idx >= 0:
        return parsed_choice, parsed_idx, reason

    norm_raw = normalize_choice_text(raw_choice)
    if not norm_raw:
        return "", -1, "empty"

    for idx, c in enumerate(LT_ELE_CHOICES):
        if normalize_choice_text(c).lower() == norm_raw.lower():
            return c, idx, "exact"

    if allow_fuzzy:
        best_choice, best_idx, score = _best_fuzzy_match(norm_raw, LT_ELE_CHOICES)
        if best_idx >= 0 and score >= 0.70:
            return best_choice, best_idx, f"fuzzy({score:.2f})"

    return norm_raw, -1, "unresolved"


def resolve_post_dec(raw_choice: str, allow_fuzzy: bool = True) -> Tuple[str, str]:
    parsed_choice, parsed_idx, reason = _parse_numeric_choice(raw_choice, POST_DEC_CHOICES)
    if parsed_idx >= 0:
        return parsed_choice, reason

    norm_raw = normalize_choice_text(raw_choice)
    if not norm_raw:
        return "", "empty"

    for c in POST_DEC_CHOICES:
        if normalize_choice_text(c).lower() == norm_raw.lower():
            return c, "exact"

    if allow_fuzzy:
        best_choice, best_idx, score = _best_fuzzy_match(norm_raw, POST_DEC_CHOICES)
        if best_idx >= 0 and score >= 0.70:
            return best_choice, f"fuzzy({score:.2f})"

    return norm_raw, "unresolved"

