# RADIUS_Drive_Bench
We introduce RADIUS-Drive (Risk-Aware DIagnostic Understanding & Safety) to evaluate safety-critical driving beyond outcome correctness. RADIUS-Drive targets the hazardous failure mode of Pseudo-Correctness, where the final action appears correct while risk triggering, key-factor localization, or validity assessment is incorrect or missing. To mitigate long-tail scarcity, we build a scalable safety-critical scenario generation pipeline that supports reference-conditioned con-trollable injection within realistic visual distributions and reference-free controllable generation, through a unified interface that binds risk elements, validity, and decision logic. To mitigate process blindness, we propose the SAR diagnostic protocol, a verifiable metacognitive chain of Safety → Awareness → Reasoning. Safety evaluates conservative baseline decisions under uncertainty, Awareness assesses risk triggering and localization by requiring identification of safety-critical anomalies and the dominant long-tail factor, and Reasoning audits causal validity and decision consistency from intermediate commitments to the final action. Accordingly, we adapt a suite of consistency-centric metrics.

## Repository Overview

This repository is organized into four primary components:

### 1) LT_scenario_gen
Safety-critical long-tail scenario generation methods. This module supports both image editing and text-to-image generation workflows.

- **Usage**: See `LT_scenario_gen/README.md` for detailed instructions.

### 2) Py_Lightweight_IVI
A lightweight IVI (in-vehicle infotainment) simulation system implemented in Python, intended for rapid prototyping and integration in evaluation pipelines.

### 3) RADIUS_benchmark
Model evaluation following the SAR (Scenario-Action-Response) process. It measures multiple capability dimensions, including:

- **Instantaneous decision-making**
- **Risk triggering and perception**
- **Effectiveness judgment**
- **Decision aggressiveness**
- **Causal consistency between perception, effectiveness commitment, and decision-making**

- **Usage**: See `RADIUS_benchmark/README.md` for detailed instructions.

### 4) RADIUS_DataSet550
The first release of the safety-critical long-tail scenario dataset, including:

- **500 safety-critical long-tail scenarios**
- **50 normal scenarios**

## Getting Started
1. Review the module-level READMEs for detailed setup and usage instructions.
2. Configure any required API keys or endpoints in the module-specific configuration files.
3. Run the generation and evaluation workflows according to your research needs.

## Contributing
Contributions are welcome. Please open an issue or submit a pull request with clear descriptions and reproducible steps.

## License
This project is released under the terms of the MIT License. The complete license text can be found in the LICENSE file located at the root of this repository.