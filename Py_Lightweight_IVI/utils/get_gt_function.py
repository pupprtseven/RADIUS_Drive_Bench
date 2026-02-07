import os,json
from Py_Lightweight_IVI.evaluation_framework.utils.io import load_scene
from Py_Lightweight_IVI.evaluation_framework.core.updater import Simulator


if __name__ == '__main__':

    file_path= "../evaluation_framework/scene_json/test2.json"
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    scene = load_scene(file_path)

    controls = {
        "vx": 0, "ay": 0
    }


    sim = Simulator(scene, file_path, duration=3.2)
    results = sim.run_get_fun(controls)
    print(results)