from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List


def _fmt_num(value: Any) -> str:
    try:
        v = float(value)
        if v.is_integer():
            return str(int(v))
        return f"{v:.2f}"
    except Exception:
        return str(value)


def parse_map_to_prompt(map_json: Dict[str, Any]) -> str:
    """Convert aligned map json into a compact prompt-friendly summary."""
    if not isinstance(map_json, dict) or not map_json:
        return "No structured map data available."

    entities = map_json.get("entities", [])
    if not isinstance(entities, list):
        entities = []

    ego = None
    others: List[Dict[str, Any]] = []
    for e in entities:
        if not isinstance(e, dict):
            continue
        if e.get("type") == "ego" and ego is None:
            ego = e
        else:
            others.append(e)

    lines: List[str] = []
    lines.append(f"entities_total={len(entities)}; non_ego={len(others)}")

    if ego:
        lines.append(
            "ego: "
            f"pos=({_fmt_num(ego.get('x', 0))}, {_fmt_num(ego.get('y', 0))}), "
            f"v=({_fmt_num(ego.get('vx', 0))}, {_fmt_num(ego.get('vy', 0))}), "
            f"yaw={_fmt_num(ego.get('yaw', 0))}"
        )

    if others:
        cnt = Counter(str(e.get("type", "unknown")) for e in others)
        counts = ", ".join([f"{k}:{v}" for k, v in cnt.most_common()])
        lines.append(f"type_counts: {counts}")

        preview: List[str] = []
        for e in others[:8]:
            et = str(e.get("type", "unknown"))
            eid = e.get("id", e.get("track_id", "N/A"))
            x = _fmt_num(e.get("x", 0))
            y = _fmt_num(e.get("y", 0))
            vx = _fmt_num(e.get("vx", 0))
            vy = _fmt_num(e.get("vy", 0))
            preview.append(f"{et}[id={eid}] pos=({x},{y}) v=({vx},{vy})")
        lines.append("objects_preview: " + " | ".join(preview))

    route = map_json.get("route") or map_json.get("planned_route")
    if route is not None:
        lines.append(f"route_hint: {route}")

    return "\n".join(lines)

