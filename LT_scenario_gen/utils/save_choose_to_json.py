import os,json

from LT_scenario_gen.utils import get_img_path


def save_to_choose_json(input_img_path, choose_value=" ", json_path="../output_pic/choose.json"):
    """
    Write the structure {"choose": "xxx", "input_image_path": "..."} to choose.json

    :param input_img_path: Image path
    :param choose_value: Value of the "choose" field (passed according to actual requirements)
    :param json_path: Save path
    """
    choose_data = {
        "choose": choose_value,
        "input_image_path": input_img_path
    }
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = [existing_data]
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
    existing_data.append(choose_data)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    image_relative_paths = get_img_path.process_image_paths("../bc2")
    for img_path in image_relative_paths:
        save_to_choose_json(img_path,choose_value="", json_path="../output_pic3/choose.json")