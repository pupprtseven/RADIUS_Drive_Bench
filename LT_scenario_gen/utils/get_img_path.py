import os


def process_image_paths(folder_path):
    """
    Traverse the folder to obtain the relative paths of all images (relative to the current working directory), with the path separator unified as '/'.

    :param folder_path: Path of the folder to be traversed (supports relative or absolute paths)
    :return: List of relative paths for images (using '/' as the separator)
    """
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff')

    folder_abs = os.path.abspath(folder_path)
    current_work_dir = os.getcwd()

    image_relative_paths = []

    for root, _, files in os.walk(folder_abs):
        for file in files:
            if file.lower().endswith(image_extensions):
                file_abs = os.path.join(root, file)
                file_rel = os.path.relpath(file_abs, current_work_dir)
                file_rel = file_rel.replace(os.sep, '/')
                image_relative_paths.append(file_rel)


    return image_relative_paths


