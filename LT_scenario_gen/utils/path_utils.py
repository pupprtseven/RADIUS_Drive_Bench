from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "dataset_gen"
UTILS_DIR = PROJECT_ROOT / "utils"
PROMPT_DIR = PROJECT_ROOT / "prompt"
INPUT_DIR = PROJECT_ROOT / "input_img"
OUTPUT_DIR = PROJECT_ROOT / "output_img"
ERROR_LOG_PATH = PROJECT_ROOT / "error_log.txt"


def resolve_from(base_dir: Path, maybe_relative_path: str | Path) -> Path:
    path = Path(maybe_relative_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def load_json_file(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_dataset_config() -> dict:
    return load_json_file(DATASET_DIR / "file_path.json")


def load_api_config() -> dict:
    return load_json_file(UTILS_DIR / "config.json")
