import os
from pathlib import Path


def process_image_paths(folder_path):
    """
    Traverse the folder and return absolute paths for all images.

    :param folder_path: Path of the folder to be traversed (supports relative or absolute paths)
    :return: List of absolute image paths
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')

    folder_abs = Path(folder_path).resolve()

    image_relative_paths = []

    for root, _, files in os.walk(folder_abs):
        for file in files:
            if file.lower().endswith(image_extensions):
                file_abs = Path(root) / file
                image_relative_paths.append(str(file_abs.resolve()))


    return image_relative_paths


