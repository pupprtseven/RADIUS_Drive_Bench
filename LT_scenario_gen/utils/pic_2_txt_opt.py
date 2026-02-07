import os
import re
import base64
import requests
import json

"""
The function of this file is to specify the modification category and generate modified prompts.
input： pic & opt
output: prompt

"""




def read_prompt_from_file(file_path: str, opt_value: str = None) -> str:
    if not os.path.exists(file_path):
        example_prompt = "Describe this image focusing on the {opt} aspects."
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(example_prompt)
        print(f"⚠️ {file_path} not found, sample file created automatically. Please modify it and try again.")
        return example_prompt.replace("{opt}", opt_value or "")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read().strip()
        if not text:
            raise ValueError(f"❌ {file_path} is empty, please fill in the prompt.")
        if "{opt}" in text:
            if opt_value is None:
                raise ValueError("❌ prompt.txt contains {opt} but OPT_VALUE is not provided.")
            text = text.replace("{opt}", opt_value)
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


def generate_text_from_image(model_name: str, api_key: str, base_url: str, prompt: str, input_image_path: str, name_mode: str = "auto",mName: str="analysis_1"):
    if name_mode == "manual":
        task_name = mName
    else:
        task_name = get_next_logname()


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

    print("Image modification in progress.......")
    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if response.status_code != 200:
        print(f"❌ request failed: {response.status_code}")
        print(response.text)
        return

    response_json = response.json()

    try:
        text_output = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print("❌ Failed to extract text output")
        print(json.dumps(response_json, indent=2, ensure_ascii=False))
        return


    return text_output

