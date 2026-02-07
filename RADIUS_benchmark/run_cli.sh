#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AutoDrive Benchmark Runner (post decision-making E2E)
# - Uses the refactored pipeline: perception -> instant decision -> post decision-making (E2E)
# - No Stage3 mode juggling; a single E2E pass handles long-tail + acc factors + effective factors + post-level
# - Secrets are NOT hardcoded; set BENCH_API_KEY in your env when BENCH_USE_MOCK=0
# ============================================================

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

# ============ Required ============
                         

: "${BENCH_BASE_URL:=}"
: "${BENCH_JUDGE_BASE_URL:=}"
: "${BENCH_API_KEY:=}"
: "${BENCH_API_KEYS:=}"
: "${BENCH_JUDGE_API_KEY:=}"
: "${BENCH_JUDGE_API_KEYS:=}"
: "${BENCH_RESUME:=0}"                  # 1=skip finished samples
: "${BENCH_TEMP_FLOOR:=0}"              # >0 to floor temps (useful for providers rejecting 0.0)
: "${BENCH_ANALYSIS_MODE:=}"            # set to longtail_assist to skip instant decision

# If you did not `pip install -e .`, point this to the directory that CONTAINS `autodrive_benchmark/`.
# In this repo layout, that directory is simply the parent of this script.
: "${BENCH_PKG_DIR:=${SCRIPT_DIR}/..}"

# ============ Optional ============
: "${BENCH_MODEL:=gpt-4o}"
: "${BENCH_JUDGE_MODEL:=gpt-4o-mini}"
: "${BENCH_USE_MOCK:=0}"                 # 1=mock, 0=live
: "${BENCH_PREFIX:=data}"
: "${BENCH_WORKERS:=20}"

: "${BENCH_IDX_START:=1}"
: "${BENCH_IDX_END:=550}"
# Explicit indices (comma-separated), e.g. "15,59,65". Used when BENCH_SAMPLE_MODE=list.
: "${BENCH_IDX_LIST:=1,2,3,4,5,6,7,8,9,10}"

# Where to write outputs (default: ./results/<model> under current working directory).
# Note: the dataset is still read from BENCH_BASE_DIR.
: "${BENCH_OUTPUT_DIR:=$(pwd)/results/${BENCH_MODEL//\//_}}"

# Optional toggles (match BenchmarkConfig fields)
: "${BENCH_USE_LLM_JUDGE:=1}"            # 1=on, 0=off (post-dec level judge)
: "${BENCH_USE_JSON_MODE:=1}"            # 1=on, 0=off
: "${BENCH_ENABLE_VISION:=1}"            # 1=on, 0=off
: "${BENCH_VISION_DETAIL:=high}"         # low|high
: "${BENCH_MAX_TOKENS:=4096}"

: "${BENCH_SAVE_INDIVIDUAL:=1}"          # 1=save per-sample json, 0=off
: "${BENCH_ENABLE_COLOR:=1}"             # 1=colored logs, 0=off

export BENCH_BASE_DIR BENCH_BASE_URL BENCH_JUDGE_BASE_URL BENCH_API_KEY BENCH_API_KEYS BENCH_JUDGE_API_KEY BENCH_JUDGE_API_KEYS BENCH_RESUME BENCH_TEMP_FLOOR
export BENCH_MODEL BENCH_JUDGE_MODEL BENCH_USE_MOCK BENCH_PREFIX
export BENCH_IDX_START BENCH_IDX_END BENCH_IDX_LIST BENCH_OUTPUT_DIR
export BENCH_USE_LLM_JUDGE BENCH_USE_JSON_MODE BENCH_ENABLE_VISION BENCH_VISION_DETAIL BENCH_MAX_TOKENS
export BENCH_SAVE_INDIVIDUAL BENCH_ENABLE_COLOR BENCH_WORKERS
export BENCH_ANALYSIS_MODE


# Sampling mode:
# - range: use BENCH_IDX_START..BENCH_IDX_END
# - random: sample by GT is_longtail (see BENCH_RANDOM_*)
# - list: use BENCH_IDX_LIST
# - gt_false: filter to GT is_longtail=False within the candidate list
# - gt_true: filter to GT is_longtail=True within the candidate list
: "${BENCH_SAMPLE_MODE:=range}"
: "${BENCH_RANDOM_M:=10}"
: "${BENCH_RANDOM_N:=0}"
: "${BENCH_RANDOM_SEED:=42}"
: "${BENCH_RANDOM_FROM_ALL:=1}"
export BENCH_SAMPLE_MODE BENCH_RANDOM_M BENCH_RANDOM_N BENCH_RANDOM_SEED BENCH_RANDOM_FROM_ALL

if [[ "${BENCH_USE_MOCK}" != "1" && -z "${BENCH_API_KEY}" && -z "${BENCH_API_KEYS}" ]]; then
  echo "[ERROR] BENCH_API_KEY or BENCH_API_KEYS is required when BENCH_USE_MOCK=0" >&2
  exit 2
fi

echo "[RUN] pkg_dir=${BENCH_PKG_DIR}"
echo "[RUN] base_dir=${BENCH_BASE_DIR}"
echo "[RUN] output_dir=${BENCH_OUTPUT_DIR}"
echo "[RUN] model=${BENCH_MODEL} judge=${BENCH_JUDGE_MODEL} mock=${BENCH_USE_MOCK}"
echo "[RUN] idx=${BENCH_IDX_START}..${BENCH_IDX_END}"
echo "[RUN] idx_list=${BENCH_IDX_LIST}"
echo "[RUN] sample_mode=${BENCH_SAMPLE_MODE}"
echo "[RUN] json_mode=${BENCH_USE_JSON_MODE} vision=${BENCH_ENABLE_VISION} vision_detail=${BENCH_VISION_DETAIL} max_tokens=${BENCH_MAX_TOKENS}"
echo "[RUN] llm_judge=${BENCH_USE_LLM_JUDGE} save_individual=${BENCH_SAVE_INDIVIDUAL}"
echo "[RUN] workers=${BENCH_WORKERS}"

# Ensure the package can be imported
export PYTHONPATH="${BENCH_PKG_DIR}:${PYTHONPATH:-}"

python3 -m autodrive_benchmark.cli
