import os,json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from LT_scenario_gen.utils.path_utils import OUTPUT_DIR


def save_to_json(text1, input_img_path, json_path=OUTPUT_DIR / "opt.json"):
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "best": "non",
        "second": "non",
        "other": "non",
        "input_image_path": input_img_path
    }

    if ";" in text1 and ":" in text1:
        parts = [p.strip() for p in text1.split(";") if p.strip()]

        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                key = key.strip().lower()
                value = value.strip()


                if key in result:
                    result[key] = value

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    data.append(result)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

