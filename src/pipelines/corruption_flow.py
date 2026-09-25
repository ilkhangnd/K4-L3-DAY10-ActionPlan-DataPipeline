from __future__ import annotations

import hashlib
import json

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run deterministic corruption, automated repair, and comparison."""
    settings = load_settings()
    paths = settings.paths
    _require_baseline(paths)

    baseline_metrics = read_json(paths.baseline_metrics)
    baseline_df = pd.read_json(paths.clean_json)
    test_set_hash_before = _file_sha256(paths.eval_testset)
    print(f"[1/8] Baseline loaded: {len(baseline_df)} rows; test_set_sha256={test_set_hash_before[:12]}")

    corrupted_df = corrupt_clean_dataframe(baseline_df, paths.corruption_log)
    write_csv(corrupted_df, paths.corrupted_clean_csv)
    corrupted_df.to_json(paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"[2/8] Six corruptions injected: {len(baseline_df)} -> {len(corrupted_df)} rows")

    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.corrupted_freshness_report
    )
    repair_triggered = not corrupted_quality["success"]
    print(
        f"[3/8] Corrupted gate: gx_success={corrupted_quality['gx_success']} "
        f"is_fresh={corrupted_freshness['is_fresh']} -> auto_repair={repair_triggered}"
    )
    if not repair_triggered:
        raise RuntimeError("The controlled corruption did not trigger the quality/freshness gate.")

    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.corrupted_metrics,
        answers_output_path=paths.corrupted_answers,
    )
    corrupted_metrics = corrupted_bundle.summary
    print(f"[4/8] Corrupted evaluation: {_metric_line(corrupted_metrics)}")

    # Automated repair always starts from the immutable raw-record artifact.
    # Building twice with one fixed run date proves idempotence explicitly.
    raw_records = load_raw_records(paths.raw_records_json)
    repair_run_date = now_utc()
    repaired_df = build_clean_dataframe(raw_records, repair_run_date)
    repeated_repair_df = build_clean_dataframe(raw_records, repair_run_date)
    pd.testing.assert_frame_equal(repaired_df, repeated_repair_df, check_dtype=True)
    repaired_hash = _dataframe_sha256(repaired_df)
    repeated_hash = _dataframe_sha256(repeated_repair_df)
    baseline_hash = _dataframe_sha256(baseline_df)
    write_csv(repaired_df, paths.repaired_clean_csv)
    repaired_df.to_json(paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"[5/8] Repair rebuilt {len(repaired_df)} rows from raw; idempotent=True")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.repaired_freshness_report
    )
    if not repaired_quality["success"]:
        raise RuntimeError(f"Repaired data failed the quality gate; see {paths.repaired_quality_report}")

    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.repaired_metrics,
        answers_output_path=paths.repaired_answers,
    )
    repaired_metrics = repaired_bundle.summary
    test_set_hash_after = _file_sha256(paths.eval_testset)
    if test_set_hash_after != test_set_hash_before:
        raise RuntimeError("The fixed evaluation set changed during corruption/repair.")

    verification = {
        "generated_at": now_utc().isoformat(),
        "repair_source": paths.raw_records_json.relative_to(paths.project_dir).as_posix(),
        "repair_triggered_by_failed_gate": repair_triggered,
        "repair_runs_compared": 2,
        "idempotent": repaired_hash == repeated_hash,
        "baseline_matches_repaired": baseline_hash == repaired_hash,
        "baseline_dataframe_sha256": baseline_hash,
        "first_repair_dataframe_sha256": repaired_hash,
        "second_repair_dataframe_sha256": repeated_hash,
        "test_set_unchanged": test_set_hash_before == test_set_hash_after,
        "test_set_sha256": test_set_hash_after,
    }
    write_json(paths.repair_verification, verification)
    print(f"[6/8] Repaired evaluation: {_metric_line(repaired_metrics)}")

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print("[7/8] Three-state comparison")
    _print_comparison(baseline_metrics, corrupted_metrics, repaired_metrics)
    print(f"[8/8] Report written -> {paths.comparison_report}")


def _require_baseline(paths) -> None:
    required = (
        paths.raw_records_json,
        paths.clean_json,
        paths.eval_testset,
        paths.baseline_metrics,
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Run 'python script/run_phase1.py' first. Missing baseline artifacts: "
            + ", ".join(missing)
        )


def _dataframe_sha256(df: pd.DataFrame) -> str:
    payload = json.dumps(
        df.to_dict(orient="records"), sort_keys=True, ensure_ascii=False, default=str,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _file_sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric_line(metrics: dict) -> str:
    return (
        f"hit_rate={metrics['retrieval_hit_rate']:.2f} "
        f"token_f1={metrics['mean_token_f1']:.2f} "
        f"judge_accuracy={metrics['judge_accuracy']:.2f} "
        f"judge_score={metrics['mean_judge_score']:.2f}"
    )


def _print_comparison(baseline: dict, corrupted: dict, repaired: dict) -> None:
    print(f"{'Metric':<24} {'Baseline':>10} {'Corrupted':>10} {'Repaired':>10}")
    print("-" * 58)
    for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(
            f"{key:<24} {baseline[key]:>10.4f} {corrupted[key]:>10.4f} {repaired[key]:>10.4f}"
        )
