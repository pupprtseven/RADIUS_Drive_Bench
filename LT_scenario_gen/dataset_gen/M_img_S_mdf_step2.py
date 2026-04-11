from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import modified_to_obtain
from LT_scenario_gen.utils import get_img_path
from LT_scenario_gen.utils.path_utils import DATASET_DIR, load_dataset_config, resolve_from

config = load_dataset_config()
INPUT_IMAGE_PATH = resolve_from(DATASET_DIR, config.get("input_image_path"))
OUTPUT_IMAGE_PATH = resolve_from(DATASET_DIR, config.get("output_image_path"))

def mism_step2(I):
    image_relative_paths = get_img_path.process_image_paths(INPUT_IMAGE_PATH)
    for img_path in image_relative_paths:
        print("Sheet", I, ": ", img_path)
        I=I+1
        modified_to_obtain.modified_img(img_path, OUTPUT_IMAGE_PATH)

if __name__ == '__main__':
    mism_step2(1)
