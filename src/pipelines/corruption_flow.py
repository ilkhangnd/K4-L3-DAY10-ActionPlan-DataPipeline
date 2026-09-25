from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd
from pandas.testing import assert_frame_equal

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run corruption, evaluate its impact, and rebuild clean state from raw data."""
    settings = load_settings()
    _require_baseline_artifacts(settings)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality = read_json(settings.paths.baseline_quality_report)
    baseline_freshness = read_json(settings.paths.freshness_report)
    clean_df = pd.read_json(settings.paths.clean_json)

    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_bundle = evaluate_pipeline(
        settings,
        corrupted_index,
        settings.paths.eval_testset,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    # Idempotent repair: discard the altered dataframe and rebuild solely from
    # the preserved raw-record artifact, then write to separate repair paths.
    test_set_before = settings.paths.eval_testset.read_bytes()
    repair_run_date = datetime.now(UTC)
    repaired_df = build_clean_dataframe(
        load_raw_records(settings.paths.raw_records_json), repair_run_date
    )
    repaired_repeat_df = build_clean_dataframe(
        load_raw_records(settings.paths.raw_records_json), repair_run_date
    )
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_bundle = evaluate_pipeline(
        settings,
        repaired_index,
        settings.paths.eval_testset,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    write_json(
        settings.paths.repair_verification,
        {
            "repair_triggered_by_failed_gate": not bool(corrupted_quality["success"]),
            "idempotent": _dataframes_match(repaired_df, repaired_repeat_df),
            "baseline_matches_repaired": _dataframes_match(clean_df, repaired_df),
            "test_set_unchanged": test_set_before == settings.paths.eval_testset.read_bytes(),
        },
    )

    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
    )
    print("Corruption flow complete: baseline, corrupted, and repaired artifacts are ready.")
    print(f"Comparison report: {settings.paths.comparison_report}")


def _dataframes_match(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    """Return whether two dataframes have the same values and column order."""
    try:
        assert_frame_equal(left.reset_index(drop=True), right.reset_index(drop=True), check_dtype=False)
    except AssertionError:
        return False
    return True


def _require_baseline_artifacts(settings) -> None:
    required = (
        settings.paths.clean_json,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_quality_report,
        settings.paths.freshness_report,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Baseline artifacts are missing. Run 'python script/run_phase1.py' first: " + ", ".join(missing)
        )
