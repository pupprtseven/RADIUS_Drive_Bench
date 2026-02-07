from __future__ import annotations

import base64
from pathlib import Path


class ImageEncoder:
    """Encode local images as base64 for multimodal API payloads."""

    def encode(self, image_path: str) -> str:
        p = Path(image_path)
        if not p.exists() or not p.is_file():
            return ""
        try:
            data = p.read_bytes()
        except Exception:
            return ""
        return base64.b64encode(data).decode("ascii")

