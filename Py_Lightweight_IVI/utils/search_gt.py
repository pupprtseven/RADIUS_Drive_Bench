import os
import json
from Py_Lightweight_IVI.evaluation_framework.utils.io import load_scene
from Py_Lightweight_IVI.evaluation_framework.core.updater import Simulator


if __name__ == '__main__':

    # Path to the input scene JSON file
    file_path = "YOUR_PATH_HERE"

    # Extract file name without extension (used for naming outputs)
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    # Load scene configuration and entities from JSON
    scene = load_scene(file_path)

    # Generate a list of ego control combinations (vx, ay)
    # vx: longitudinal velocity
    # ay: longitudinal acceleration
    control_list_63 = [
        {"vx": vx, "ay": ay}
        for vx in [-100, -65, -35, 0, 35, 65, 100]
        for ay in [-300, -150, -75, -30, 0, 30, 75, 150, 225]
    ][:63]  # Limit to the first 63 control combinations

    # Initialize simulator with a fixed duration
    sim_36 = Simulator(scene, file_path, duration=3.2)

    # Run simulations for all ego control combinations
    all_results_36 = sim_36.run_multiple_ego_controls(control_list_63)

    # Filter out control combinations that result in no collisions
    valid_controls = [r["control"] for r in all_results_36 if not r["collisions"]]

    # Ensure each valid control has a label field
    for control in valid_controls:
        if "label" not in control:
            control["label"] = ""  # Default label (can be customized if needed)

    # Output directory for ground-truth results
    output_folder = "YOUR_PATH_HERE"  # Modify this path if a different output location is desired
    os.makedirs(output_folder, exist_ok=True)

    # Derive a short name for the output file
    base_name = os.path.splitext(os.path.basename(file_path))[0]  # e.g., "11_aligned"
    short_name = base_name.replace("_aligned", "")  # e.g., "11"

    # Full path to the output ground-truth JSON file
    output_path = os.path.join(output_folder, f"{short_name}_gt.json")

    # Construct ground-truth JSON structure
    gt_json = {
        "source_scene": file_path,
        "num_total_controls": len(control_list_63),
        "num_valid_controls": len(valid_controls),
        "valid_controls": valid_controls
    }

    # Save ground-truth results to disk
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(gt_json, f, ensure_ascii=False, indent=2)

    # Status messages
    print(f"✔ GT JSON has been successfully generated: {output_path}")
    print(f"✔ {len(valid_controls)}/{len(control_list_63)} control combinations are collision-free")
