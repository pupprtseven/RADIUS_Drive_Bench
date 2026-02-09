# AutoDrive Benchmark

A modular benchmark framework for evaluating autonomous-driving long-tail reasoning and decision quality with LLMs.

## Overview

This project evaluates a two-stage driving intelligence pipeline:

1. Instant decision-making (select `(vx, ay)` control action from candidate space)
2. Long-tail reasoning + post-decision planning (taxonomy, long-tail element, ACC factors, post decision level)

It supports:

- Vision-capable LLM inference (image + structured map prompt)
- Mock mode for offline/CI verification
- Batch execution with resumable outputs
- Optional LLM-as-Judge for post-decision level scoring
- Multiple sampling modes (`range`, `random`, `list`, `gt_true`, `gt_false`)

## Repository Structure

```text
autodrive_benchmark/
├── cli.py                  # Module entrypoint: reads env vars and starts batch run
├── runner.py               # Batch orchestration, sampling, resume, summary
├── config.py               # BenchmarkConfig dataclass
├── models.py               # Pipeline result / score models
├── constants.py            # Taxonomy, labels, choice sets, mappings
├── prompts.py              # Prompt templates
├── llm/
│   ├── clients.py          # OpenAI client pool + unified LLM caller
│   └── judge.py            # LLM-as-Judge service
├── pipeline/
│   └── benchmark.py        # Core two-stage benchmark pipeline
├── scoring/
│   └── scorer.py           # Score calculation logic
├── utils/                  # Parsing and normalization helpers
├── run_cli.sh              # Shell launcher with environment defaults
└── requirements.txt
```

## Data Layout

`BENCH_BASE_DIR` must point to a dataset root with this structure:

```text
<dataset_root>/
├── pic/
│   ├── <prefix><idx>.png
├── json/
│   ├── <prefix><idx>.json                        # text GT (includes is_longtail, taxonomy, etc.)
│   ├── pre_dec_json/
│   │   ├── <prefix><idx>_aligned.json           # map json
│   └── gt_json/
│       ├── <prefix><idx>_gt.json                # valid_controls GT
```

Example with `prefix=da`, `idx=8`:

- `pic/da8.png`
- `json/da8.json`
- `json/pre_dec_json/da8_aligned.json`
- `json/gt_json/da8_gt.json`

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies are intentionally minimal (`openai>=1.30.0`).

## Quick Start

### 1) Mock mode (no API call)

```bash
export BENCH_USE_MOCK=1
export BENCH_BASE_DIR=../RADIUS_DataSet550
export BENCH_PREFIX=data
python3 -m autodrive_benchmark.cli
```

### 2) Live API mode

```bash
export BENCH_USE_MOCK=0
export BENCH_BASE_URL=https://api.openai.com/v1
export BENCH_API_KEY=<your_main_key>

# Optional separate judge endpoint/key:
export BENCH_JUDGE_BASE_URL=https://api.openai.com/v1
export BENCH_JUDGE_API_KEY=<your_judge_key>

export BENCH_MODEL=gpt-4o
export BENCH_JUDGE_MODEL=gpt-4o-mini
export BENCH_BASE_DIR=../RADIUS_DataSet550
export BENCH_PREFIX=data

python3 -m autodrive_benchmark.cli
```

### 3) Use provided launcher

```bash
chmod +x run_cli.sh
BENCH_BASE_DIR=/path/to/dataset BENCH_USE_MOCK=1 ./run_cli.sh
```

## Environment Variables

### Required in practice

- `BENCH_BASE_DIR`: dataset root directory
- `BENCH_PREFIX`: sample filename prefix (for example `da`, `dt`, `data`)
- `BENCH_USE_MOCK`: `1` for mock mode, `0` for live mode

When `BENCH_USE_MOCK=0`, provide:

- `BENCH_API_KEY` or `BENCH_API_KEYS` (comma-separated)
- optional `BENCH_BASE_URL` for custom provider endpoint

### Model and judge

- `BENCH_MODEL` (default in `cli.py`: `gpt-4o-mini`; in `run_cli.sh`: `gpt-4o`)
- `BENCH_JUDGE_MODEL`
- `BENCH_JUDGE_BASE_URL`
- `BENCH_JUDGE_API_KEY` / `BENCH_JUDGE_API_KEYS`

If judge-specific key/url is absent, judge falls back to main key/url.

### Sampling controls

- `BENCH_SAMPLE_MODE`: `range` | `random` | `list` | `gt_true` | `gt_false`
- `BENCH_IDX_START`, `BENCH_IDX_END` (for `range`)
- `BENCH_IDX_LIST` (for `list`, comma-separated)
- `BENCH_RANDOM_M`, `BENCH_RANDOM_N`, `BENCH_RANDOM_SEED`, `BENCH_RANDOM_FROM_ALL`

### Runtime behavior

- `BENCH_RESUME`: `1` skips samples with complete result files
- `BENCH_OUTPUT_DIR`: output folder override
- `BENCH_TEMP_FLOOR`: fallback temperature floor when configured temp is `<=0`
- `BENCH_ANALYSIS_MODE=longtail_assist`: skip instant decision and force long-tail analysis path

### API behavior

- `BENCH_USE_JSON_MODE`
- `BENCH_ENABLE_VISION`
- `BENCH_VISION_DETAIL`
- `BENCH_MAX_TOKENS`

### Notes

- `run_cli.sh` exports `BENCH_WORKERS`, but current `cli.py` does not map it into `BenchmarkConfig.workers`. Current runtime remains effectively single-worker unless config wiring is extended.

## Pipeline

### Stage 1: Instant Decision

- Input: map description + action candidates (`vx_options`, `ay_options`)
- Output: selected `(vx, ay)` and validation label against GT valid controls:
  - `0`: invalid/collision
  - `1`: optimal
  - `2`: safe alternative
  - `3`: risky
  - `4`: hazardous

### Stage 2: Long-tail Reasoning + Post Decision

- Input: image + map + selected action (or injected GT-optimal action in specific paths)
- Output fields include:
  - `is_longtail`, `level1/2/3`
  - `lt_ele`
  - `acc_factors_multi`, `acc_effective_indices`
  - `post_decision_plan`

### Special execution branches

- `analysis_longtail_assist`: forces long-tail reasoning and bypasses instant decision.
- If Stage 1 returns risky/hazardous, pipeline can inject GT label-1 control for stage-2 evaluation continuity.
- If GT is non-longtail, stage-2 may run long-tail check only.

## Scoring

Default long-tail weights sum to 100:

- `classification`: 15
- `is_longtail`: 10
- `pre_dec`: 15
- `lt_ele`: 10
- `acc_factors`: 15
- `acc_effective`: 15
- `post_dec`: 20

Additional behavior:

- Non-longtail GT uses a dedicated 50/50-style branch (`is_longtail` + `pre_dec`).
- `post_dec` level is scored via LLM-as-Judge (if enabled) or fallback mapping logic.
- Batch summary includes aggregate metrics and per-dimension averages.

## Outputs

Default output dir:

- `<BENCH_BASE_DIR>/results/<model_name_safe>/`
- or `<BENCH_OUTPUT_DIR>` if set

Generated files:

- `result_<prefix><idx>_full.json`: per-sample full result (if enabled)
- `batch_summary.json`: aggregate statistics + compact sample summaries

## Programmatic Usage

```python
from RADIUS_benchmark import BenchmarkConfig, BenchmarkRunner

config = BenchmarkConfig(
    use_mock=True,
    sample_prefix="da",
)
runner = BenchmarkRunner(base_dir="../RADIUS_DataSet550", config=config)
runner.run([1, 2, 3])
summary = runner.get_summary_dict()
print(summary["statistics"])
```

## Troubleshooting

- `No API key provided`: set `BENCH_API_KEY` or `BENCH_API_KEYS` when not in mock mode.
- `Skipping <id>: missing required files`: verify all four required files exist for each sample.
- JSON parse failures: keep `BENCH_USE_JSON_MODE=1`; if provider does not support it, client retries without strict JSON mode.
- Vision-related provider errors: client retries text-only path when multimodal is unsupported.

## License

This project is released under the terms of the MIT License. The complete license text can be found in the LICENSE file located at the root of this repository.