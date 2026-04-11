import os
import re
import base64
import requests
import json


def validate_prompt(prompt: str, context: str = "prompt") -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError(f"{context} is empty or missing")
    return prompt.strip()

"""
Based on the image, recommend the category
Input: Image
Output: Category recommendation

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

def read_prompt_from_file_image(file: str, img_value: str = None) -> str:
    text = file
    if "{image}" in text:
        if img_value is None:
            raise ValueError("❌ prompt.txt contains {image} but image_VALUE is not provided.")
        text = text.replace("{image}", img_value)
    return text


def encode_image_to_base64(image_path: str) -> str:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"❌ Input image not found: {image_path}")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_next_logname(prefix="image_text_", ext=".txt") -> str:
    idx = 1
    while os.path.exists(f"{prefix}{idx:03d}{ext}"):
        idx += 1
    return f"{prefix}{idx:03d}"


def generate_text_from_image(model_name: str,api_key: str, base_url: str, prompt: str, input_image_path: str, name_mode: str = "auto",mName: str="analysis_1"):
    if name_mode == "manual":
        task_name = mName
    else:
        task_name = get_next_logname()

    prompt = read_prompt_from_file_image(prompt, input_image_path)
    prompt = validate_prompt(prompt, "Category recommendation prompt")


    image_b64 = encode_image_to_base64(input_image_path)

    # === Payload ===
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": f"data:image/png;base64,{image_b64}"}
                ]
            }
        ]
    }
    print("Category recommendation.......")
    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if False and response.status_code != 200:
        print(f"❌ request failed: {response.status_code}")
        print(response.text)
        return

    if response.status_code != 200:
        raise RuntimeError(
            f"Category recommendation request failed: {response.status_code} {response.text}"
        )

    response_json = response.json()

    try:
        text_output = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print("❌ Failed to extract text output")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        raise RuntimeError(
            "Failed to extract text output from category recommendation response: "
            + json.dumps(response_json, ensure_ascii=False)
        )
        return



    return text_output
