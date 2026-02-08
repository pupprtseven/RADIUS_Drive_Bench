import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ============================================================
# Configuration (Modify here if needed)
# ============================================================

INPUT_DIR = Path(r"YOUR_PATH_HERE")     # Folder containing input JSON files
OUTPUT_DIR = Path(r"YOUR_PATH_HERE")  # Folder to save aligned JSON files
# ============================================================


# ============================================================
# Vehicle shape-to-attribute mapping
# (width, height) -> (toward, size)
# ============================================================
VEHICLE_MAPPING = {
    (90, 230): ("0", "Small"),
    (230, 90): ("1", "Small"),
    (130, 400): ("0", "Big"),
    (400, 130): ("1", "Big"),
    (35, 90): ("0", "Nm"),
    (90, 35): ("1", "Nm"),
}

# Thresholds for size inference
BIG_THRESHOLD = 300
NM_THRESHOLD = 90


def norm_val(v: Any) -> int:
    """
    Normalize a numeric value:
    - Take absolute value
    - Convert to integer
    - Return 0 if conversion fails
    """
    try:
        return int(abs(float(v)))
    except Exception:
        return 0


def decide_vehicle_toward_size(w: int, h: int) -> Tuple[str, str]:
    """
    Decide vehicle orientation (toward) and size class based on width and height.

    Args:
        w (int): Bounding box width
        h (int): Bounding box height

    Returns:
        toward (str): "0" or "1", indicating vehicle heading
        size (str): One of {"Big", "Small", "Nm"}
    """
    # Try exact mapping first
    key = (w, h)
    if key in VEHICLE_MAPPING:
        return VEHICLE_MAPPING[key]

    # Try swapped width-height
    rev_key = (h, w)
    if rev_key in VEHICLE_MAPPING:
        return VEHICLE_MAPPING[rev_key]

    # Infer orientation: taller -> toward 0, wider -> toward 1
    toward = "0" if w < h else "1"

    # Infer size based on the larger dimension
    if max(w, h) >= BIG_THRESHOLD:
        size = "Big"
    elif max(w, h) <= NM_THRESHOLD:
        size = "Nm"
    else:
        size = "Small"

    return toward, size


def transform_entities(input_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transform raw detection entities into a unified simulation scene format.

    Args:
        input_list (List[Dict]): Raw entity list from input JSON

    Returns:
        Dict[str, Any]: Aligned scene description compatible with simulator
    """
    # Scene-level configuration
    out = {
        "width": 1000,
        "height": 2000,
        "dt": 0.2,
        "entities": []
    }

    veh_count = 0
    obs_count = 0
    ped_count = 0

    # --------------------------------------------------------
    # Add ego vehicle if present
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # Process vehicles
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # Process pedestrians
    # --------------------------------------------------------
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

    # --------------------------------------------------------
    # Process static obstacles
    # --------------------------------------------------------
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
    """
    Process a single JSON file and save the aligned result.

    Args:
        input_path (Path): Path to input JSON file
        outdir (Path): Output directory
    """
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to read file: {input_path} -> {e}")
        return

    # Support list-based or dict-based JSON formats
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
        out_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"[OK] {input_path.name} -> {out_path.name}")
    except Exception as e:
        print(f"[ERROR] Failed to write file: {out_path} -> {e}")


def process_folder(input_folder: Path, outdir: Path):
    """
    Process all JSON files in a folder.

    Args:
        input_folder (Path): Directory containing input JSON files
        outdir (Path): Directory to save processed files
    """
    json_files = sorted(
        [p for p in input_folder.iterdir() if p.suffix.lower() == ".json"]
    )

    if not json_files:
        print(f"[WARN] No .json files found in: {input_folder}")
        return

    for jf in json_files:
        process_single_file(jf, outdir)


def main():
    """
    Entry point for batch JSON alignment.
    """
    print("Start processing JSON files...")

    if not INPUT_DIR.exists():
        print(f"[ERROR] Input directory does not exist: {INPUT_DIR}")
        return

    process_folder(INPUT_DIR, OUTPUT_DIR)
    print("All files processed successfully!")


if __name__ == "__main__":
    main()
