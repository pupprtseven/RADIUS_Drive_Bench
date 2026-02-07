import os,json
from Py_Lightweight_IVI.evaluation_framework.utils.eval import *
from Py_Lightweight_IVI.evaluation_framework.utils.io import load_scene
from Py_Lightweight_IVI.evaluation_framework.core.updater import Simulator
from Py_Lightweight_IVI.evaluation_framework.visualization.visualize import plot_scene

if __name__ == '__main__':

    file_path="scene_json/test2.json"
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    scene = load_scene(file_path)

    # Adjust vx & ay parameters here
    controls = [
        {"vx": 0, "ay": 0},
    ]

    sim = Simulator(scene, file_path, duration=3.2)
    results = sim.run_multiple_ego_controls(controls)

    json_file = file_path

    if os.path.exists(json_file):
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                json_data = json.load(f)
                if not isinstance(json_data, dict):
                    json_data = {"width": 1000, "height": 2000, "dt": 0.2, "entities": []}
            except json.JSONDecodeError:
                json_data = {"width": 1000, "height": 2000, "dt": 0.2, "entities": []}
    else:
        json_data = {"width": 1000, "height": 2000, "dt": 0.2, "entities": []}

    new_data = results[-1]


    ego_trajectories = [r["trajectory"] for r in results]


    plot_scene(scene, ego_trajectories=ego_trajectories, gt_trajectory=None, save_path="visualization/scene_pic",filename=file_name)
