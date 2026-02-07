import os
import json


def generate_pic_related_json(pic_dir, pre_dec_json_dir, gt_json_dir, json_output_dir, example_template_path):
    """
    Generate a JSON annotation file for each PNG image in the given image directory.

    For every image file under `pic_dir`, this function:
    1. Loads a JSON template from `example_template_path`.
    2. Fills in image-related fields (image name, relative paths to image, prediction JSON, and GT JSON).
    3. Assigns default values to auxiliary annotation fields.
    4. Writes the resulting JSON file to `json_output_dir`.

    All file paths stored in the generated JSON are relative to `json_output_dir`,
    which makes the dataset portable across different directory layouts.

    Parameters
    ----------
    pic_dir : str
        Directory containing PNG image files.
    pre_dec_json_dir : str
        Directory containing pre-decision JSON files (aligned predictions).
    gt_json_dir : str
        Directory containing ground-truth JSON files.
    json_output_dir : str
        Output directory where generated JSON files will be saved.
    example_template_path : str
        Path to the example/template JSON file used as a base structure.
    """

    # Ensure the output directory exists
    os.makedirs(json_output_dir, exist_ok=True)

    # Load the example JSON template
    with open(example_template_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    # Iterate over all PNG images in the image directory
    for pic_filename in os.listdir(pic_dir):
        if not pic_filename.endswith(".png"):
            continue  # Only process PNG files

        # Extract the base name of the image file (e.g., "XXX.png" -> "XXX")
        pic_basename = os.path.splitext(pic_filename)[0]

        # Construct absolute paths
        pic_full_path = os.path.join(pic_dir, pic_filename)
        gt_json_path = os.path.join(gt_json_dir, f"{pic_basename}_gt.json")
        pre_dec_full_path = os.path.join(pre_dec_json_dir, f"{pic_basename}_aligned.json")

        # Convert absolute paths to paths relative to the JSON output directory
        # Formula: os.path.relpath(target_path, base_path)
        relative_pic_path = os.path.relpath(pic_full_path, json_output_dir)
        relative_gt_json_path = os.path.relpath(gt_json_path, json_output_dir)
        relative_pre_dec_path = os.path.relpath(pre_dec_full_path, json_output_dir)

        # Create a new JSON object based on the template and populate required fields
        new_json = template.copy()
        new_json["pic_name"] = pic_basename          # Original image base name
        new_json["pic_path"] = relative_pic_path     # Relative path to the image file
        new_json["pre_dec_file"] = relative_pre_dec_path  # Relative path to pre-decision JSON
        new_json["gt_json_file"] = relative_gt_json_path  # Relative path to GT JSON

        # Fill in other fields with default values (can be customized later)
        new_json["is_longtail"] = "True"
        new_json["Sup_description"] = ""
        new_json["lt_ele"] = ""
        new_json["acc_factors"] = ""
        new_json["COT"] = ""
        new_json["post_dec"] = ""
        new_json["is_transfer2p"] = "No"

        # Save the generated JSON file
        output_json_path = os.path.join(json_output_dir, f"{pic_basename}.json")
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(new_json, f, indent=2, ensure_ascii=False)

    print(f"All image-related JSON files have been generated and saved to: {json_output_dir}")


def uniform_rename_files(pic_dir, pre_dec_json_dir, gt_json_dir, json_dir):
    """
    Uniformly rename related files in multiple directories and update JSON contents accordingly.

    This function processes corresponding groups of files:
    - Image file:            XXX.png
    - Pre-decision JSON:     XXX_aligned.json
    - Ground-truth JSON:     XXX_gt.json
    - Metadata JSON:         XXX.json

    Each group is renamed sequentially to:
    - data1.png, data2.png, ...
    - data1_aligned.json, ...
    - data1_gt.json, ...
    - data1.json, ...

    After renaming, the function updates the internal fields of the JSON files to:
    - Reflect the new base name (dataX)
    - Maintain relative paths with respect to `json_dir`

    Parameters
    ----------
    pic_dir : str
        Directory containing image files.
    pre_dec_json_dir : str
        Directory containing pre-decision JSON files.
    gt_json_dir : str
        Directory containing ground-truth JSON files.
    json_dir : str
        Directory containing metadata JSON files (used as the relative path base).
    """

    # Collect all valid file groups (image + pre-decision JSON + GT JSON + metadata JSON)
    file_groups = []
    for json_filename in os.listdir(json_dir):
        if not json_filename.endswith(".json"):
            continue

        json_basename = os.path.splitext(json_filename)[0]

        # Construct corresponding file paths
        pic_path = os.path.join(pic_dir, f"{json_basename}.png")
        pre_dec_path = os.path.join(pre_dec_json_dir, f"{json_basename}_aligned.json")
        gt_json_path = os.path.join(gt_json_dir, f"{json_basename}_gt.json")
        json_path = os.path.join(json_dir, json_filename)

        # Only include groups where required files exist
        if os.path.exists(pic_path) and os.path.exists(pre_dec_path):
            file_groups.append((pic_path, pre_dec_path, gt_json_path, json_path, json_basename))
        else:
            print(f"Warning: Missing pic/pre_dec files for {json_basename}, skipping this entry.")

    # Rename files sequentially and update JSON content
    for idx, (pic_path, pre_dec_path, gt_json_path, json_path, old_basename) in enumerate(file_groups, start=1):
        new_basename = f"data{idx}"

        # 1. Rename image file (XXX.png -> dataX.png)
        new_pic_path = os.path.join(pic_dir, f"{new_basename}.png")
        os.rename(pic_path, new_pic_path)

        # 2. Rename pre-decision JSON file (XXX_aligned.json -> dataX_aligned.json)
        new_pre_dec_path = os.path.join(pre_dec_json_dir, f"{new_basename}_aligned.json")
        os.rename(pre_dec_path, new_pre_dec_path)

        # 3. Rename ground-truth JSON file (XXX_gt.json -> dataX_gt.json)
        new_gt_json_path = os.path.join(gt_json_dir, f"{new_basename}_gt.json")
        os.rename(gt_json_path, new_gt_json_path)

        # 4. Rename metadata JSON file (XXX.json -> dataX.json)
        new_json_path = os.path.join(json_dir, f"{new_basename}.json")
        os.rename(json_path, new_json_path)

        # Compute new relative paths (relative to json_dir)
        relative_new_pic_path = os.path.relpath(new_pic_path, json_dir)
        relative_new_pre_dec_path = os.path.relpath(new_pre_dec_path, json_dir)

        # Update fields inside the metadata JSON file
        with open(new_json_path, "r+", encoding="utf-8") as f:
            json_data = json.load(f)
            json_data["pic_name"] = new_basename
            json_data["pic_path"] = relative_new_pic_path
            json_data["pre_dec_file"] = relative_new_pre_dec_path
            json_data["gt_json_file"] = new_gt_json_path
            f.seek(0)
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            f.truncate()

        # Update the corresponding ground-truth JSON file
        new_gt_json_path_local = os.path.join(gt_json_dir, f"{new_basename}_gt.json")
        with open(new_gt_json_path_local, "r+", encoding="utf-8") as f:
            json_data = json.load(f)
            json_data["source_scene"] = relative_new_pre_dec_path
            f.seek(0)
            json.dump(json_data, f, indent=2, ensure_ascii=False)
            f.truncate()

    print(f"Completed uniform renaming and JSON updates for {len(file_groups)} file groups.")


if __name__ == "__main__":

    pic_dir = "pic"
    pre_dec_json_dir = "json/pre_dec_json"
    gt_json_dir = "json/gt_json"
    json_dir = "json"
    example_template_path = "example.json"

    # Step 1: Generate JSON files corresponding to each image
    # generate_pic_related_json(pic_dir, pre_dec_json_dir, gt_json_dir, json_dir, example_template_path)

    # Step 2: Uniformly rename files and update JSON contents
    uniform_rename_files(pic_dir, pre_dec_json_dir, gt_json_dir, json_dir)
