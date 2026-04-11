import os
import re
import base64
import requests
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from LT_scenario_gen.utils.path_utils import OUTPUT_DIR, PROMPT_DIR, load_api_config


def validate_prompt(prompt: str, context: str = "prompt") -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{context} is empty or missing")
    return prompt.strip()


def extract_image_content(response_json: dict) -> str:
    try:
        return response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        pass

    try:
        image_item = response_json["data"][0]
        if isinstance(image_item, dict) and image_item.get("b64_json"):
            return image_item["b64_json"]
    except (KeyError, IndexError, TypeError):
        pass

    raise RuntimeError(
        "Failed to extract image content from text-to-image response: "
        + json.dumps(response_json, ensure_ascii=False)
    )

# ====================================
"""
According to natural language description, complete the modification of the image
Input: Natural Language
Output: Image
"""

config = load_api_config()

API_KEY = config.get("OPENAI_API_KEY")
BASE_URL = config.get("BASE_URL")


if not API_KEY or not BASE_URL:
    raise ValueError("Missing required configurations in config.json")


MODEL_NAME1 = "gemini-2.5-flash"
MODEL_NAME2 = "gemini-3-pro-image"
PROMPT_FILE = PROMPT_DIR / "Directly generate images.txt"


MODE = "auto"

MANUAL_FILENAME = "my_gemini_banana.png"
# =============================================


def read_prompt_from_file_desc_opt(file_path: str, desc_value: str = None,opt_value: str = None) -> str:

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

        if "{desc}" in text:
            if desc_value is None:
                raise ValueError(
                    "❌ {desc} is included in the prompt, but no opt_value was provided."
                )
            text = text.replace("{desc}", desc_value)

        if "{opt}" in text:
            if opt_value is None:
                raise ValueError(
                    "❌ {opt} is included in the prompt, but no opt_value was provided."
                )
            text = text.replace("{opt}", opt_value)
        return text


def extract_and_save_base64(content: str, save_path: str):
    match = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", content)
    if match:
        b64_data = match.group(1)
    else:
        b64_data = content.strip()

    try:
        image_bytes = base64.b64decode(b64_data)
        with open(save_path, "wb") as f:
            f.write(image_bytes)

        if image_bytes.startswith(b"\x89PNG"):
            print(f"✅ Image saved successfully as PNG file: {save_path}")
        else:
            print(f"⚠️ Warning: The image has been saved, but the file header is not PNG. Please check: {save_path}")
    except Exception as e:
        print(f"❌ Base64 failed: {e}")


def get_next_filename(folder: str, prefix="image_", ext=".png") -> str:
    os.makedirs(folder, exist_ok=True)
    existing_files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(ext)]
    if not existing_files:
        next_index = 1
    else:
        indices = []
        for f in existing_files:
            num_match = re.search(rf"{prefix}(\d+){ext}", f)
            if num_match:
                indices.append(int(num_match.group(1)))
        next_index = max(indices, default=0) + 1
    return os.path.join(folder, f"{prefix}{next_index:03d}{ext}")


def gemini_image_gen_1(prompt:str):
    prompt = validate_prompt(prompt, "Text-to-image planning prompt")
    url = f"{BASE_URL.rstrip('/')}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME1,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if response.status_code != 200:
        print(f"❌ request failed: {response.status_code}")
        print(response.text)
        raise RuntimeError(
            f"Text-to-image planning request failed: {response.status_code} {response.text}"
        )
        return

    if False and response.status_code != 200:
        raise RuntimeError(
            f"Text-to-image planning request failed: {response.status_code} {response.text}"
        )

    response_json = response.json()

    try:
        text_output = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print("❌ Failed to extract text output")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        raise RuntimeError(
            "Failed to extract text output from text-to-image planning response: "
            + json.dumps(response_json, ensure_ascii=False)
        )
        return

    return text_output


def gemini_image_gen_2(prompt: str, filename_mode: str = "auto"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prompt = validate_prompt(prompt, "Text-to-image generation prompt")

    if filename_mode == "manual":
        output_path = os.path.join(OUTPUT_DIR, MANUAL_FILENAME)
    else:
        output_path = get_next_filename(OUTPUT_DIR)

    url = f"{BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME2,
        "messages": [{"role": "user", "content": prompt}],
    }

    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        print(f"❌ request failed: {response.status_code}")
        print(response.text)
        raise RuntimeError(
            f"Text-to-image generation request failed: {response.status_code} {response.text}"
        )
        return

    if response.status_code != 200:
        raise RuntimeError(
            f"Text-to-image generation request failed: {response.status_code} {response.text}"
        )

    response_json = response.json()
    print("✅ ")
    print(json.dumps(response_json, indent=2, ensure_ascii=False)[:600], "...\n")

    content = extract_image_content(response_json)
    if False:
        content = response_json["choices"][0]["message"]["content"]
    if False:
        print("❌ Failed to extract the content field")
        return

    extract_and_save_base64(content, output_path)


if __name__ == "__main__":
    try:
        desc="Enter your natural language description"
        opt="Enter your OPT here"
        prompt_text1 = read_prompt_from_file_desc_opt(PROMPT_FILE,desc_value=desc,opt_value=opt)
        prompt_text2 = gemini_image_gen_1(prompt_text1)
        gemini_image_gen_2(prompt_text2, filename_mode=MODE)
    except Exception as e:
        print(f"❌ Program runtime error: {e}")
