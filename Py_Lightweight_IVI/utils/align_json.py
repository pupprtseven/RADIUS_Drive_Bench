import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ---- 配置：直接修改这里即可 ----
# INPUT_DIR = Path(r"../BZ_front")     # 输入文件夹
# OUTPUT_DIR = Path(r"../BZ_end")  # 输出文件夹
INPUT_DIR = Path(r"../input_json")     # 输入文件夹
OUTPUT_DIR = Path(r"../bc2/json/pre_dec_json")  # 输出文件夹
# -----------------------------------

VEHICLE_MAPPING = {
    (90, 230): ("0", "Small"),
    (230, 90): ("1", "Small"),
    (130, 400): ("0", "Big"),
    (400, 130): ("1", "Big"),
    (35, 90): ("0", "Nm"),
    (90, 35): ("1", "Nm"),
}

BIG_THRESHOLD = 300
NM_THRESHOLD = 90


def norm_val(v: Any) -> int:
    """绝对值 + 取整"""
    try:
        return int(abs(float(v)))
    except Exception:
        return 0


def decide_vehicle_toward_size(w: int, h: int) -> Tuple[str, str]:
    key = (w, h)
    if key in VEHICLE_MAPPING:
        return VEHICLE_MAPPING[key]
    rev_key = (h, w)
    if rev_key in VEHICLE_MAPPING:
        return VEHICLE_MAPPING[rev_key]

    toward = "0" if w < h else "1"

    if max(w, h) >= BIG_THRESHOLD:
        size = "Big"
    elif max(w, h) <= NM_THRESHOLD:
        size = "Nm"
    else:
        size = "Small"

    return toward, size


def transform_entities(input_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = {
        "width": 1000,
        "height": 2000,
        "dt": 0.2,
        "entities": []
    }

    veh_count = 0
    obs_count = 0
    ped_count = 0

    # ego
    if any(item.get("label") == "ego" for item in input_list):
        out["entities"].append({
            "id": "ego",
            "type": "ego",
            "toward": "0",
            "x": 500,
            "y": 0,
            "size": "Small",
            "vx": 0,
            "vy": 0,
            "ay": 0,
            "accel_mode": "Z"
        })

    # veh
    for item in input_list:
        if item.get("label") == "veh":
            veh_count += 1
            w = norm_val(item.get("width", 0))
            h = norm_val(item.get("height", 0))
            cx = norm_val(item.get("centerX", 0))
            cy = norm_val(item.get("centerY", 0))
            toward, size = decide_vehicle_toward_size(w, h)

            out["entities"].append({
                "id": f"veh_{veh_count}",
                "type": "vehicle",
                "toward": toward,
                "x": cx,
                "y": cy,
                "size": size,
                "vx": 0,
                "vy": 0,
                "ay": 0,
                "accel_mode": "Z"
            })

    # ped
    for item in input_list:
        if item.get("label") == "ped":
            ped_count += 1
            cx = norm_val(item.get("centerX", 0))
            cy = norm_val(item.get("centerY", 0))

            out["entities"].append({
                "id": f"ped_{ped_count}",
                "type": "pedestrian",
                "x": cx,
                "y": cy,
                "vx": 0,
                "vy": 0
            })

    # obs
    for item in input_list:
        if item.get("label") == "obs":
            obs_count += 1
            cx = norm_val(item.get("centerX", 0))
            cy = norm_val(item.get("centerY", 0))
            w = norm_val(item.get("width", 0))
            h = norm_val(item.get("height", 0))

            out["entities"].append({
                "id": f"obs_{obs_count}",
                "type": "obstacle",
                "x": cx,
                "y": cy,
                "width": w,
                "length": h
            })

    return out


def process_single_file(input_path: Path, outdir: Path):
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] 读取失败: {input_path} -> {e}")
        return

    # 支持顶层 list 或 dict
    if isinstance(data, list):
        input_list = data
    elif isinstance(data, dict) and isinstance(data.get("entities"), list):
        input_list = data["entities"]
    else:
        input_list = [data]

    result = transform_entities(input_list)

    outdir.mkdir(parents=True, exist_ok=True)
    out_name = input_path.stem + "_aligned.json"
    out_path = outdir / out_name

    try:
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] {input_path.name} -> {out_path.name}")
    except Exception as e:
        print(f"[ERROR] 写入失败: {out_path} -> {e}")


def process_folder(input_folder: Path, outdir: Path):
    json_files = sorted([p for p in input_folder.iterdir() if p.suffix.lower() == ".json"])
    if not json_files:
        print(f"[WARN] 文件夹中没有 .json 文件: {input_folder}")
        return

    for jf in json_files:
        process_single_file(jf, outdir)


def main():
    print("开始处理 JSON 文件...")
    if not INPUT_DIR.exists():
        print(f"[ERROR] 输入文件夹不存在: {INPUT_DIR}")
        return

    process_folder(INPUT_DIR, OUTPUT_DIR)
    print("全部完成！")


if __name__ == "__main__":
    main()
