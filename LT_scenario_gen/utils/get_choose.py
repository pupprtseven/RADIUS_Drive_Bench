import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from LT_scenario_gen.utils.path_utils import OUTPUT_DIR


def get_choose_by_filename(target_filename, json_path=OUTPUT_DIR / "choose.json"):
    """
    Retrieve the corresponding 'choose' value from choose.json based on the image filename (e.g., image2.png).

    :param target_filename: Filename of the target image (filename only, no path included)
    :param json_path: Path to choose.json
    :return: Corresponding 'choose' value (str); returns None if no matching entry is found
    """
    json_path = Path(json_path)

    if not os.path.exists(json_path):
        print(f"Error: File {json_path} does not exist")
        return None

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = [data]
    except json.JSONDecodeError:
        print(f"Error: Invalid format for {json_path}, unable to parse")
        return None

    for item in data:
        if "input_image_path" not in item or "choose" not in item:
            continue

        item_filename = os.path.basename(item["input_image_path"])

        if item_filename == target_filename:
            return item["choose"]

    print(f"Error: No corresponding 'choose' value found for {target_filename}")
    return None
