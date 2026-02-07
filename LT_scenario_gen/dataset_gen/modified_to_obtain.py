import os
import re
import base64
import requests
import datetime
import json
from LT_scenario_gen.utils import (
    pic_2_txt_opt,
    pic_2_txt,
    pic_2_pic,
    save_opt_to_json,
    save_choose_to_json,
    get_choose,
)

# Load configuration file (API keys and service endpoint)
with open("../utils/config.json", "r") as f:
    config = json.load(f)

API_KEY = config.get("OPENAI_API_KEY")
BASE_URL = config.get("BASE_URL")

# Validate required configuration entries
if not API_KEY or not BASE_URL:
    raise ValueError("Missing required configuration in config.json")

# Prompt template files
PROMPT_FILE_1 = "../prompt/Category_suggestion.txt"
PROMPT_FILE_2 = "../prompt/Generate_modification_suggestions.txt"

# Model identifiers
MODEL_NAME_1 = "gemini-2.5-flash"
MODEL_NAME_2 = "gemini-3-pro-image"

# Naming / execution modes
MODE = "auto"
MANUAL_NAME = "analysis_1"


def read_prompt_from_file(file_path: str) -> str:
    """
    Read a prompt string from a text file.

    If the file does not exist, a sample prompt is automatically created
    to help the user understand the expected format.

    Parameters
    ----------
    file_path : str
        Path to the prompt text file.

    Returns
    -------
    str
        The prompt content as a non-empty string.

    Raises
    ------
    ValueError
        If the file exists but is empty.
    """
    if not os.path.exists(file_path):
        example_prompt = "Make the background a fancy Gemini-themed restaurant with glowing lights."
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(example_prompt)
        print(
            f"⚠️ File {file_path} not found. "
            f"A sample file has been created automatically. "
            f"Please modify it and try again."
        )
        return example_prompt

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            raise ValueError(f"❌ {file_path} is empty. Please fill in the prompt.")
        return text


def read_prompt_from_file_opt(file_path: str, opt_value: str = None) -> str:
    """
    Read a prompt template from a file and optionally substitute the `{opt}` placeholder.

    If the file does not exist, a template containing `{opt}` is automatically created.
    When `{opt}` appears in the prompt, `opt_value` must be provided.

    Parameters
    ----------
    file_path : str
        Path to the prompt template file.
    opt_value : str, optional
        Value used to replace the `{opt}` placeholder in the prompt.

    Returns
    -------
    str
        The processed prompt string.

    Raises
    ------
    ValueError
        If the file exists but is empty, or if `{opt}` is present but no opt_value is provided.
    """
    if not os.path.exists(file_path):
        example_prompt = "Describe this image focusing on the {opt} aspects."
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(example_prompt)
        print(
            f"⚠️ {file_path} not found. "
            f"A sample file has been auto-created. "
            f"Please modify it and try again."
        )
        return example_prompt.replace("{opt}", opt_value or "")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            raise ValueError(f"❌ {file_path} is empty. Please fill in the prompt.")

        # Replace the {opt} placeholder if present
        if "{opt}" in text:
            if opt_value is None:
                raise ValueError(
                    "❌ {opt} is included in the prompt, but no opt_value was provided."
                )
            text = text.replace("{opt}", opt_value)
        return text


def category_suggestion(input_image_path: str, name_mode: str = "auto"):
    """
    Generate category suggestions for an input image using a vision-language model.

    The generated textual output is saved to a JSON file, and an initial
    (empty) selection record is created for downstream processing.

    Parameters
    ----------
    input_image_path : str
        Path to the input image.
    name_mode : str, optional
        Naming mode used when saving intermediate results.
    """
    try:
        prompt_text1 = read_prompt_from_file(PROMPT_FILE_1)
        text1 = pic_2_txt.generate_text_from_image(
            MODEL_NAME_1,
            API_KEY,
            BASE_URL,
            prompt_text1,
            input_image_path,
            name_mode=name_mode,
            mName=MANUAL_NAME,
        )

        # Save generated options and initialize the choice JSON
        save_opt_to_json.save_to_json(
            text1, input_image_path, json_path="../output_pic/opt.json"
        )
        save_choose_to_json.save_to_choose_json(
            input_image_path, choose_value="", json_path="../output_pic/choose.json"
        )

    except Exception as e:
        # Print error message to console
        error_msg = f"❌ Program runtime error: {e}"
        print(error_msg)

        # Error logging configuration
        log_file = "../error_log.txt"
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Construct detailed log content
        log_content = (
            f"========================================\n"
            f"Time: {current_time}\n"
            f"Image path: {input_image_path}\n"
            f"Error message: {str(e)}\n"
            f"========================================\n\n"
        )

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Append log entry
        with open(log_file, "a+", encoding="utf-8") as f:
            f.write(log_content)

        print(f"📝 Error log has been recorded to: {os.path.abspath(log_file)}")


def modified_img(input_image_path: str, output_image_path: str, name_mode: str = "auto"):
    """
    Modify an input image based on a previously selected option.

    This function:
    1. Retrieves the selected modification option for the image.
    2. Generates a modification prompt conditioned on that option.
    3. Produces a new image using an image-to-image generation model.
    4. Logs detailed error information if any step fails.

    Parameters
    ----------
    input_image_path : str
        Path to the original input image.
    output_image_path : str
        Directory where the modified image will be saved.
    name_mode : str, optional
        Naming mode used for generated outputs.
    """

    img_name = os.path.basename(input_image_path)

    # Retrieve the chosen modification option for this image
    opt = get_choose.get_choose_by_filename(
        img_name, json_path="../output_pic1/choose1.json"
    )

    if opt == "non":
        print("⚠️ This image cannot be modified.")
        return

    try:
        prompt_text2 = read_prompt_from_file_opt(PROMPT_FILE_2, opt)
        mPrompt = pic_2_txt_opt.generate_text_from_image(
            MODEL_NAME_1,
            API_KEY,
            BASE_URL,
            prompt_text2,
            input_image_path,
            name_mode=name_mode,
            mName=MANUAL_NAME,
        )
    except Exception as e:
        error_msg = f"❌ Program runtime error: {e}"
        print(error_msg)

        log_file = "../error_log.txt"
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_content = (
            f"========================================\n"
            f"Time: {current_time}\n"
            f"Image path: {input_image_path}\n"
            f"Error message: {str(e)}\n"
            f"========================================\n\n"
        )

        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        with open(log_file, "a+", encoding="utf-8") as f:
            f.write(log_content)

        print(f"📝 Error log recorded to: {os.path.abspath(log_file)}")
        return

    # Model explicitly indicates that no modification should be applied
    if mPrompt == "NO":
        print("❌ This image cannot be modified.")
        return

    print(mPrompt)

    try:
        pic_2_pic.generate_image_from_image(
            MODEL_NAME_2,
            API_KEY,
            BASE_URL,
            mPrompt,
            input_image_path,
            output_image_path,
            opt,
            filename_mode=name_mode,
            mName=MANUAL_NAME,
        )
    except Exception as e:
        error_msg = f"❌ Program runtime error: {e}"
        print(error_msg)

        log_file = "../error_log.txt"
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_content = (
            f"========================================\n"
            f"Time: {current_time}\n"
            f"Image path: {input_image_path}\n"
            f"Error message: {str(e)}\n"
            f"========================================\n\n"
        )

        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        with open(log_file, "a+", encoding="utf-8") as f:
            f.write(log_content)

        print(f"📝 Error log has been recorded to: {os.path.abspath(log_file)}")


if __name__ == "__main__":
    input_image_path = "../input_img"
    output_image_path = "../output_img"

    # Step 1: Generate category suggestions for the input image
    # category_suggestion(input_image_path)

    # Step 2: Modify the image based on the selected option
    modified_img(input_image_path, output_image_path)
