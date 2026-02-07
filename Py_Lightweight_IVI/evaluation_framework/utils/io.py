import json
from Py_Lightweight_IVI.evaluation_framework.core.entitys import Vehicle, Pedestrian, StaticObstacle, Entity
from Py_Lightweight_IVI.evaluation_framework.core.scene import Scene


def load_json(path: str):
    with open(path, 'r') as f:
        return json.load(f)


def save_json(path: str, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def load_scene(path: str) -> Scene:
    data = load_json(path)
    scene = Scene(width=data.get("width", 1000), height=data.get("height", 3000), dt=data.get("dt", 0.2))

    for e in data["entities"]:
        etype = e["type"]
        if etype in ("vehicle", "ego"):
            scene.add_entity(Vehicle.from_json(e))
        elif etype == "pedestrian":
            scene.add_entity(Pedestrian.from_json(e))
        elif etype == "obstacle":
            scene.add_entity(StaticObstacle.from_json(e))
        else:
            scene.add_entity(Entity.from_json(e))
    return scene
