# Py_Lightweight_IVI

Py_Lightweight_IVI is a **lightweight, Python-based in-vehicle intelligence (IVI) simulation framework** designed to support **safety-critical evaluation workflows** in autonomous driving research.  
It is primarily developed to serve the **S (Simulation) phase** of the **Safety → Awareness → Reasoning (SAR)** diagnostic pipeline.

The framework emphasizes **simplicity, extensibility, and transparency**, enabling rapid prototyping and controlled experimentation without the overhead of full-scale driving simulators.

---

## Project Structure

```text
Py_Lightweight_IVI/
├── evaluation_framework/
│   ├── core/
│   ├── entitys/
│   ├── utils/
│   └── ...
├── utils/
├── TODO/
└── README.md

# Core Components

## 1. evaluation_framework/
This folder contains the core lightweight IVI simulation system, fully implemented in Python.

### Purpose
The **evaluation_framework** is designed to:
* Simulate simplified traffic scenes involving vehicles, pedestrians, and static obstacles
* Support rapid rollout of multiple ego-vehicle control strategies
* Detect collisions and record safety-relevant outcomes
* Serve as the simulation backbone for the SAR S-phase

Unlike high-fidelity simulators (e.g., CARLA, LGSVL), this framework focuses on:
* Minimal dependencies
* Deterministic behavior
* Easy modification and inspection
* Tight integration with data-driven safety evaluation pipelines

### Key Characteristics
* **Lightweight:** No physics engines or rendering dependencies
* **Modular:** Clear separation between scene, entities, dynamics, and evaluation logic
* **Extensible:** New entity types, motion models, or safety metrics can be added with minimal effort
* **Research-oriented:** Designed for diagnostic evaluation rather than visual realism

---

## 2. evaluation_framework/core/
This module contains the core simulation loop and control logic, including:
* Scene update and time stepping
* Ego-vehicle control rollout
* Simulation scheduling
* Collision detection orchestration

It defines how simulation steps are executed and how intermediate and final results are collected for downstream analysis.

---

## 3. evaluation_framework/entitys/
This folder defines the semantic entities used in the simulation:
* Vehicle
* Pedestrian
* StaticObstacle
* Entity (base class)

Each entity encapsulates:
* Spatial attributes
* Motion states
* Per-step update rules

This abstraction enables clear reasoning about interactions among different traffic participants.

---

## 4. evaluation_framework/utils/
This module provides shared utilities, including:
* Geometry handling
* Collision checking
* Coordinate transformation
* Scene serialization and deserialization

All utilities are intentionally kept simple and transparent to facilitate debugging, inspection, and research experimentation.

---

# Auxiliary Tooling (In Progress)

## utils/ and TODO/ Directories
The `utils` and `TODO` folders contain ongoing and experimental tools related to:
* Map modeling
* Semi-automatic dataset annotation
* Scenario preprocessing utilities

> **Important Note**
> These components are under active development and are not required for using the core simulation framework.
> 
> Their presence does not affect any existing functionality in `evaluation_framework`.

Future releases will gradually introduce:
* Richer map abstractions
* Annotation assistance pipelines
* Improved scenario construction tools

---

# Role in the SAR Pipeline
**Py_Lightweight_IVI** is explicitly designed to support the:
**S (Simulation)** phase of the **Safety → Awareness → Reasoning (SAR)** framework.

Within SAR:
* **Safety** focuses on scenario construction and safety-critical inputs
* **Simulation (S)** evaluates candidate behaviors under controlled dynamics
* **Awareness** and **Reasoning** analyze perception and decision-making quality

Py_Lightweight_IVI provides a controlled, interpretable simulation layer that bridges safety-critical scenario generation and higher-level reasoning evaluation.

---

# Design Philosophy
* **Minimalism over realism:** Prioritize controllability and interpretability rather than photorealistic simulation.
* **Research-first:** Tailored for ablation studies, counterfactual testing, and diagnostic benchmarks.
* **Composable:** Designed to integrate smoothly with external scenario generators, planners, and evaluation pipelines.

---

# Future Work
Planned extensions include:
* Richer motion models
* Configurable interaction rules
* Scenario-level safety metrics
* Map-aware simulation support
* Automated annotation and labeling tools

These features will be released incrementally without breaking existing APIs.

---

# License
This project is intended for research and academic use. 
License information will be provided in future releases.