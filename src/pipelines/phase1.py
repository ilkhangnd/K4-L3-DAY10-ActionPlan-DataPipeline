from __future__ import annotations

from datetime import UTC, datetime

from core.config import load_settings
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Run the full clean-corpus baseline and write every Phase 1 artifact."""
    settings = load_settings()
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    df = build_clean_dataframe(records, datetime.now(UTC))
    if df.empty:
        raise RuntimeError("The cleaning phase produced no valid records; baseline evaluation cannot continue.")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise RuntimeError("Baseline data failed the quality gate. Inspect data/quality/baseline_quality_report.json.")

    index = LocalEmbeddingIndex.build(df, settings)
    # A refreshed source changes paper IDs and titles, so its benchmark must
    # be regenerated in the same run to keep ground truth aligned with Chroma.
    test_set = load_or_create_test_set(
        df,
        settings.paths.eval_testset,
        refresh=settings.refresh_test_set or settings.refresh_source,
    )
    clean_doc_ids = set(df["paper_id"].astype(str))
    test_doc_ids = {
        str(doc_id)
        for sample in test_set.samples
        for doc_id in sample.get("ground_truth_doc_ids", [])
    }
    if not test_doc_ids.issubset(clean_doc_ids):
        test_set = load_or_create_test_set(df, settings.paths.eval_testset, refresh=True)
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    source_summary = {
        "source": settings.source_api,
        "query": settings.source_query,
        "raw_records": len(records),
        "clean_records": len(df),
        "collection_name": index.collection_name,
        "embedding_model": settings.embedding_model,
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"Phase 1 complete: {len(df)} clean records, {len(test_set)} benchmark questions.")
    print(f"Baseline metrics: {settings.paths.baseline_metrics}")
    print(f"Baseline report: {settings.paths.baseline_report}")
