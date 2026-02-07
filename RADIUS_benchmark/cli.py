from __future__ import annotations

import os

from .config import BenchmarkConfig
from .runner import BenchmarkRunner
from .logging_utils import get_logger


def _split_keys(env_name: str, single_fallback: str) -> list[str]:
    raw = os.environ.get(env_name, "")
    items = [k.strip() for k in raw.split(",") if k.strip()]
    if items:
        return items
    fallback = os.environ.get(single_fallback, "").strip()
    return [fallback] if fallback else []


def main() -> None:

    api_keys = _split_keys("BENCH_API_KEYS", "BENCH_API_KEY")
    judge_api_keys = _split_keys("BENCH_JUDGE_API_KEYS", "BENCH_JUDGE_API_KEY")

    config = BenchmarkConfig(
        base_url=os.environ.get("BENCH_BASE_URL", ""),
        api_key=os.environ.get("BENCH_API_KEY", ""),
        api_keys=api_keys,
        judge_model_base_url=os.environ.get("BENCH_JUDGE_BASE_URL", ""),
        judge_model_api_key=os.environ.get("BENCH_JUDGE_API_KEY", ""),
        judge_api_keys=judge_api_keys,
        model=os.environ.get("BENCH_MODEL", "gpt-4o-mini"),
        judge_model=os.environ.get("BENCH_JUDGE_MODEL", "gpt-4o-mini"),
        use_mock=os.environ.get("BENCH_USE_MOCK", "0") == "1",
        sample_prefix=os.environ.get("BENCH_PREFIX", "da"),
        enable_color=True,
        save_individual_results=True,
        resume=os.environ.get("BENCH_RESUME", "0") == "1",
        temp_floor=float(os.environ.get("BENCH_TEMP_FLOOR", "0") or 0),
        pre_decision_input=["blind", "cascaded", "oracle_gt"],
        output_dir=os.environ.get("BENCH_OUTPUT_DIR", ""),
        analysis_longtail_assist=os.environ.get("BENCH_ANALYSIS_MODE", "").strip().lower() == "longtail_assist",
    )

    base_dir = os.environ.get("BENCH_BASE_DIR", "./dataset")
    idx_start = int(os.environ.get("BENCH_IDX_START", "1"))
    idx_end = int(os.environ.get("BENCH_IDX_END", "10"))
    idx_list = list(range(idx_start, idx_end + 1))

    runner = BenchmarkRunner(base_dir, config)

    sample_mode = os.environ.get("BENCH_SAMPLE_MODE", "range").strip().lower()
    if sample_mode == "random":
        # Randomly select m long-tail (is_longtail==True) and n non-long-tail samples by GT.
        m_true = int(os.environ.get("BENCH_RANDOM_M", "50"))
        n_false = int(os.environ.get("BENCH_RANDOM_N", "50"))
        seed = int(os.environ.get("BENCH_RANDOM_SEED", "0"))

        # If requested, sample from all available GT files, ignoring idx_start/idx_end.
        if os.environ.get("BENCH_RANDOM_FROM_ALL", "0") == "1":
            candidates = runner.list_available_indices()
        else:
            candidates = idx_list

        idx_list = runner.sample_random_by_is_longtail(candidates, m_true=m_true, n_false=n_false, seed=seed)
    elif sample_mode == "gt_false":
        idx_list = runner.filter_by_gt_is_longtail(idx_list, target_is_longtail=False, require_all_files=True)
    elif sample_mode == "gt_true":
        idx_list = runner.filter_by_gt_is_longtail(idx_list, target_is_longtail=True, require_all_files=True)
    elif sample_mode == "list":
        raw = os.environ.get("BENCH_IDX_LIST", "").strip()
        if not raw:
            raise SystemExit("BENCH_SAMPLE_MODE=list but BENCH_IDX_LIST is empty")
        idx_list = [int(x.strip()) for x in raw.split(",") if x.strip()]

    results = runner.run(idx_list)

    if results:
        get_logger().success(f"Completed! Results saved to: {runner.ensure_output_dir()}")
    else:
        get_logger().warning("No results produced.")


if __name__ == "__main__":
    main()
