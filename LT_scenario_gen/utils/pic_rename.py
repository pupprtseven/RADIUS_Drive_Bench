import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from LT_scenario_gen.utils.path_utils import OUTPUT_DIR


def rename_images_to_c(folder_path):
    """
    Rename all images in the folder to c1, c2, ..., cn (retain the original file extensions)

    :param folder_path: Path of the folder where the images are located
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')

    image_files = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.lower().endswith(image_extensions):
            image_files.append(filename)

    if not image_files:
        print("No image files found in the folder")
        return

    image_files.sort()

    for i, old_filename in enumerate(image_files, start=1):
        _, ext = os.path.splitext(old_filename)
        new_filename = f"g{i}{ext}"
        old_path = os.path.join(folder_path, old_filename)
        new_path = os.path.join(folder_path, new_filename)

        if os.path.exists(new_path):
            print(f"Skip {old_filename}: new filename {new_filename} already exists")
            continue

        os.rename(old_path, new_path)
        print(f"Renamed: {old_filename} → {new_filename}")


def rename_images(folder_path):
    """
    Rename PNG images in the specified folder: extract the last two parts separated by underscores from the original filename as the new name
    Example: ".._sec_2_b98_3.1.2.png" → "b98_3.1.2.png"
    """
    if not os.path.isdir(folder_path):
        print(f"❌ Error: Folder '{folder_path}' does not exist")
        return

    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(".png"):
            continue

        parts = filename.split("_")
        if len(parts) < 2:
            print(f"⚠️ Skip '{filename}': filename format does not meet the requirements")
            continue
        new_name = "_".join(parts[-2:])

        old_path = os.path.join(folder_path, filename)
        new_path = os.path.join(folder_path, new_name)

        if os.path.exists(new_path):
            print(f"⚠️ Skip '{filename}': new name '{new_name}' already exists")
            continue

        try:
            os.rename(old_path, new_path)
            print(f"✅ Renamed successfully: {filename} → {new_name}")
        except Exception as e:
            print(f"❌ Rename failed for '{filename}': {str(e)}")

if __name__ == "__main__":


    target_folder = OUTPUT_DIR

    rename_images(target_folder)
