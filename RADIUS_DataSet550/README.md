# RADIUS_DataSet550

RADIUS_DataSet550 is the first release of the safety-critical long-tail driving scenario dataset. It contains **550 instances** in total, including **500 safety-critical long-tail scenes** and **50 normal scenes**.

## Dataset Contents
Each instance **X** is released as an image plus JSON sidecars:

- `dataX.png`: the rendered driving scene.
- `dataX.json`: taxonomy and post-decision supervision, including:
  - classification (Level-3)
  - `lt_ele` (dominant element)
  - `acc_factors`
  - `post_dec` (reference level and/or plan text)
- `dataX_aligned.json`: simulator-ready coarse state for Phase-1 Safety (map/relations/kinematics abstraction).
- `dataX_gt.json`: pre-decision action tags for Phase-1 scoring (per-action collision/hazard/safe, and optional best action).

## Design Principles
The schema is intentionally minimal:

- `dataX_aligned.json` is only as complex as needed for deterministic Safety rollout.
- `dataX.json` carries the Phase-2/3 labels required for SAR diagnosis and cross-phase consistency metrics.

## Directory Structure
```
RADIUS_DataSet550/
├── json/                # JSON sidecars for each instance
├── pic/                 # Rendered scene images
├── aligned_dataset.py   # Utility script for alignment
├── example.json
├── example_plot.png
└── README.md
```

## Notes
- File naming follows the `dataX.*` convention across image and JSON sidecars.
- For benchmark usage, refer to the `RADIUS_benchmark` module documentation.

## License
This project is released under the terms of the MIT License. The complete license text can be found in the LICENSE file located at the root of this repository.