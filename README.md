# RADIUS_Drive_Bench
We introduce RADIUS-Drive (Risk-Aware DIagnostic Understanding & Safety) to evaluate safety-critical driving beyond outcome correctness. RADIUS-Drive targets the hazardous failure mode of Pseudo-Correctness, where the final action appears correct while risk triggering, key-factor localization, or validity assessment is incorrect or missing. To mitigate long-tail scarcity, we build a scalable safety-critical scenario generation pipeline that supports reference-conditioned con-trollable injection within realistic visual distributions and reference-free controllable generation, through a unified interface that binds risk elements, validity, and decision logic. To mitigate process blindness, we propose the SAR diagnostic protocol, a verifiable metacognitive chain of Safety → Awareness → Reasoning. Safety evaluates conservative baseline decisions under uncertainty, Awareness assesses risk triggering and localization by requiring identification of safety-critical anomalies and the dominant long-tail factor, and Reasoning audits causal validity and decision consistency from intermediate commitments to the final action. Accordingly, we adapt a suite of consistency-centric metrics.

## Repository Overview

This repository provides the official implementation and resources for **RADIUS-Drive**,  
a risk-aware diagnostic benchmark for consistency-centric evaluation in safety-critical autonomous driving.

The repository is organized into four primary components, covering **scenario generation**, **lightweight system simulation**, **diagnostic evaluation**, and **benchmark datasets**.

---

### 1) LT_scenario_gen

Safety-critical **long-tail scenario generation** module for RADIUS-Drive.

This component supports scalable construction of rare and risk-critical driving scenarios, enabling controlled evaluation beyond outcome correctness. It includes:

- **Reference-based injection**, where risk factors are explicitly injected into existing scenes
- **Reference-free generation**, where long-tail scenarios are synthesized without explicit anchors

These generation pipelines provide **auditable ground truth** for downstream diagnostic evaluation.

- **Usage**: See `LT_scenario_gen/README.md` for detailed setup and generation instructions.

---

### 2) Py_Lightweight_IVI

A lightweight **Python-based IVI (in-vehicle infotainment) simulation framework** designed to support rapid evaluation and prototyping.

This module serves as a minimal yet extensible execution environment for:
- Integrating perception, reasoning, and decision outputs from autonomous driving agents
- Supporting the **SAR (Safety → Awareness → Reasoning)** diagnostic workflow
- Enabling reproducible evaluation without dependence on full-scale simulators

The framework is intentionally lightweight to facilitate extensibility and rapid experimentation.

---

### 3) RADIUS_benchmark

The core **diagnostic evaluation framework** of RADIUS-Drive.

This module evaluates models under the proposed **SAR diagnostic protocol**, assessing not only decision outcomes but also the internal consistency of risk perception and reasoning.

The benchmark measures multiple capability dimensions, including:

- **Safety triggering** under risk-critical conditions  
- **Risk awareness and localization**
- **Effectiveness and commitment judgment**
- **Decision aggressiveness and conservativeness**
- **Cross-phase causal consistency** between Safety, Awareness, and Reasoning (Pseudo-Correctness diagnosis)

Consistency-centric metrics such as **CF-CDA**, **Guess**, and phase-wise scores are implemented to expose pseudo-correct behavior missed by outcome-only evaluation.

- **Usage**: See `RADIUS_benchmark/README.md` for evaluation pipelines and metric definitions.

---

### 4) RADIUS_DataSet550

The first public release of the **RADIUS-Drive safety-critical scenario dataset**, designed to support diagnostic evaluation of long-tail risks.

The dataset includes:

- **500 safety-critical long-tail scenarios**, covering rare but high-impact risk patterns
- **50 normal scenarios**, serving as calibration and control cases

All scenarios are paired with structured annotations to support SAR-based evaluation and consistency analysis.

---

## Getting Started

1. Review the module-level `README.md` files for detailed installation and usage instructions.
2. Configure required API keys, model endpoints, or runtime dependencies in the corresponding module configurations.
3. Run scenario generation and diagnostic evaluation workflows according to your research objectives.

---

This repository is intended for **research and benchmarking purposes**, enabling systematic analysis of pseudo-correctness and consistency failures in safety-critical autonomous driving models.

## Contributing
Contributions are welcome. Please open an issue or submit a pull request with clear descriptions and reproducible steps.

## License
This project is released under the terms of the MIT License. The complete license text can be found in the LICENSE file located at the root of this repository.