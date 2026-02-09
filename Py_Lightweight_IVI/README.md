# Py_Lightweight_IVI

Py_Lightweight_IVI is a lightweight, Python-based IVI (in-vehicle infotainment) simulation framework. It provides a minimal scene loader, basic entity modeling, and a simulator to run simple scenario rollouts, primarily for rapid prototyping and evaluation workflows.

## Features
- **Scene loading** from JSON files
- **Entity modeling** for ego vehicles, other vehicles, pedestrians, and static obstacles
- **Simulation updates** via a lightweight `Simulator`
- **Visualization** utilities for plotting trajectories

## Project Structure
```
Py_Lightweight_IVI/
├── evaluation_framework/
│   ├── core/                 # scene, entities, and simulator core
│   ├── scene_json/            # example scene definitions
│   ├── utils/                 # I/O helpers and evaluation utilities
│   ├── visualization/         # plotting utilities
│   └── main.py                # entry point for running a scene
└── utils/                     # auxiliary scripts and helpers
```

## Quick Start
1. Navigate to the evaluation framework:
   ```bash
   cd Py_Lightweight_IVI/evaluation_framework
   ```
2. Edit a scene file in `scene_json/` if needed (for example, `test2.json`).
3. Open `main.py` and adjust the control parameters (e.g., `vx`, `ay`) in `controls`.
4. Run the simulator:
   ```bash
   python main.py
   ```
5. The visualization output is saved to `visualization/scene_pic/` with the scene filename.

## Scene JSON Format (Overview)
Scene files are JSON objects with basic metadata and entity definitions. A minimal structure looks like:

```json
{
  "width": 1000,
  "height": 2000,
  "dt": 0.2,
  "entities": [
    {
      "type": "ego",
      "id": "ego",
      "x": 0,
      "y": 0,
      "vx": 0,
      "vy": 0
    }
  ]
}
```

Supported entity types include `ego`, `vehicle`, `pedestrian`, and `obstacle`.

## Auxiliary Tooling (In Progress)

## utils/ and TODO/ Directories
The `utils` and `TODO` folders contain ongoing and experimental tools related to:
* Map modeling
* Semi-automatic dataset annotation
* Scenario preprocessing utilities
These components are under active development and are not required for using the core simulation framework.
> Their presence does not affect any existing functionality in `evaluation_framework`.

## Notes
- This module is intentionally lightweight and focuses on clarity and extensibility for benchmarking pipelines.
- For integration with the full benchmark workflow, see the repository root README and the `RADIUS_benchmark` module documentation.

## License
This project is released under the terms of the MIT License. The complete license text can be found in the LICENSE file located at the root of this repository.