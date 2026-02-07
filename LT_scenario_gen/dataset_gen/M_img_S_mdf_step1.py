import os
import re
import base64
import requests
import json
import modified_to_obtain
from LT_scenario_gen.utils import get_img_path


with open("file_path.json", "r") as f:
    config = json.load(f)

INPUT_IMAGE_PATH = config.get("input_image_path")
OUTPUT_IMAGE_PATH = config.get("output_image_path")



def mism_step1():
    image_relative_paths = get_img_path.process_image_paths(INPUT_IMAGE_PATH)
    for img_path in image_relative_paths:
        modified_to_obtain.category_suggestion(img_path)
        # print(img_path)

if __name__ == '__main__':
    mism_step1()