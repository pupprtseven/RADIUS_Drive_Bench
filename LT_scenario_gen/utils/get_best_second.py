import json
import os


def get_best_second_combined(input_image_path, json_path="result.json"):
    """
    Retrieve all values from the corresponding 'best' and 'second' fields based on the input image path, and merge them into a single array.

    :param input_image_path: Relative path of the image (e.g., ../input_pic/t8.jpg)
    :param json_path: Path of the JSON file storing data
    :return: Merged numerical array (list), e.g., [3.3, 2.1, 1.3, 1.5, 3.4]; returns an empty list if no matching data is found
    """

    def get_raw_best_second(path, json_file):
        if not os.path.exists(json_file):
            return None, None
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
        except json.JSONDecodeError:
            return None, None

        for item in data:
            if "input_image_path" not in item or "best" not in item or "second" not in item:
                continue
            stored_path = item["input_image_path"].replace(os.sep, "/")
            target_path = path.replace(os.sep, "/")
            if stored_path == target_path:
                return item["best"], item["second"]
        return None, None

    best_str, second_str = get_raw_best_second(input_image_path, json_path)

    if best_str is None or second_str is None:
        print(f"No best or second data found for {input_image_path}")
        return []

    combined = []
    for num in best_str.split(","):
        num = num.strip()
        if num:
            try:
                combined.append(float(num))
            except ValueError:
                print(f"Warning: '{num}' in 'best' is not a valid number and has been skipped")
    for num in second_str.split(","):
        num = num.strip()
        if num:
            try:
                combined.append(float(num))
            except ValueError:
                print(f"Warning: '{num}' in 'second' is not a valid number and has been skipped")

    return combined


