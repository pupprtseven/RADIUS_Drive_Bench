# RADIUS_Drive_Bench

RADIUS_Drive_Bench is a research-oriented benchmark suite for safety-critical driving scenarios. It combines long-tail scenario generation, a lightweight in-vehicle infotainment (IVI) simulation environment, a standardized evaluation workflow, and an initial curated dataset.

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
No license is declared here. Please check individual modules or the repository root for licensing details.
