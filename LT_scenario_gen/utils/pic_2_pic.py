import os
import re
import base64
import mimetypes
import requests
import json


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
        if isinstance(image_item, dict):
            if image_item.get("b64_json"):
                return image_item["b64_json"]
            if image_item.get("url"):
                raise RuntimeError(
                    "Image response returned a URL instead of base64 content; "
                    "this script currently expects base64 image data."
                )
    except (KeyError, IndexError, TypeError):
        pass

    raise RuntimeError(
        "Failed to extract image content from image-edit response: "
        + json.dumps(response_json, ensure_ascii=False)
    )

# ================== 配置区域 ==================
"""
Complete the modification of the image based on the image and the corresponding prompt
Input: Images&Prompt
Output: Image

"""



def read_prompt_from_file(file_path: str) -> str:
    if not os.path.exists(file_path):
        example_prompt = "Make the background a fancy Gemini-themed restaurant with glowing lights."
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(example_prompt)
        print(f"⚠️ {file_path} not found, sample file created automatically. Please modify it and try again.")
        return example_prompt

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            raise ValueError(f"❌ {file_path} is empty, please fill in the prompt.")
        return text


def encode_image_to_base64(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"❌ Input image not found:{image_path}")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


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
            print(f"⚠️ Image saved, but the file header is not PNG: {save_path}")
    except Exception as e:
        print(f"❌ Base64 failed: {e}")


def get_next_filename(folder: str,opt: str, img_name: str ,prefix="img_", ext=".png") -> str:
    os.makedirs(folder, exist_ok=True)
    files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(ext)]
    if not files:
        idx = 1
    else:
        nums = []
        for f in files:
            m = re.search(rf"{prefix}(\d+){ext}", f)
            if m:
                nums.append(int(m.group(1)))
        idx = max(nums, default=0) + 1
    return os.path.join(folder, f"{prefix}{idx:03d}_{img_name}_{opt}{ext}")


def generate_image_from_image(model_name: str, api_key: str, base_url: str, prompt: str, input_image_path: str, output_image_path: str, opt: str, filename_mode: str = "auto",mName: str="analysis_1"):
    os.makedirs(output_image_path, exist_ok=True)
    prompt = validate_prompt(prompt, "Image edit prompt")

    if filename_mode == "manual":
        output_path = os.path.join(output_image_path, mName)
    else:
        img_name = os.path.basename(input_image_path)
        img_name = os.path.splitext(img_name)[0]
        output_path = get_next_filename(output_image_path, opt, img_name)

    if not os.path.exists(input_image_path):
        raise FileNotFoundError(f"鉂?Input image not found:{input_image_path}")


    url = f"{base_url.rstrip('/')}/images/edits"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    mime_type = mimetypes.guess_type(input_image_path)[0] or "application/octet-stream"
    data = {
        "model": model_name,
        "prompt": prompt,
    }


    print("Image modification in progress.......")
    with open(input_image_path, "rb") as image_file:
        files = [
            ("image", (os.path.basename(input_image_path), image_file, mime_type)),
        ]
        response = requests.post(url, headers=headers, data=data, files=files, timeout=550)

    if response.status_code != 200:
        print(f"❌ request failed: {response.status_code}")
        print(response.text)
        raise RuntimeError(
            f"Image edit request failed: {response.status_code} {response.text}"
        )


    response_json = response.json()

    content = extract_image_content(response_json)
    if False and False:
        content = response_json["choices"][0]["message"]["content"]
    if False:
        print("❌ Failed to extract the 'content' field")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        return

    extract_and_save_base64(content, output_path)



