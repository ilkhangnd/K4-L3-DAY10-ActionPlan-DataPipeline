from __future__ import annotations

from typing import Any

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set, load_or_create_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


DEMO_QUESTIONS = 2


def main() -> None:
    """Baseline pipeline: ingest -> clean -> quality gate -> index -> evaluate -> report."""
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    # 1-2. Raw records: reuse the preserved snapshot unless a refresh is requested.
    if settings.refresh_source or not paths.raw_records_json.exists():
        records = fetch_source_records(settings)
        source_mode = "crossref_api_or_snapshot"
    else:
        records = load_raw_records(paths.raw_records_json)
        source_mode = "raw_snapshot"
    print(f"[1/7] Raw records: {len(records)} ({source_mode})")

    # 3-4. Clean and persist.
    df = build_clean_dataframe(records, run_date)
    write_csv(df, paths.clean_csv)
    df.to_json(paths.clean_json, orient="records", indent=2, force_ascii=False)
    print(f"[2/7] Clean rows: {len(df)} -> {paths.clean_csv}")

    # 8 (run before indexing). Quality gate + freshness SLA.
    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)
    print(
        f"[3/7] Quality gate: gx_success={quality['gx_success']} "
        f"is_fresh={freshness['is_fresh']} (stale_ratio={freshness['stale_ratio']:.2%})"
    )
    if not quality["gx_success"]:
        raise RuntimeError(f"Baseline data failed the GX quality gate; see {paths.baseline_quality_report}")

    # 5. Vector index.
    index = LocalEmbeddingIndex.build(df, settings, paths.embeddings_json)
    print(f"[4/7] Chroma collection '{index.collection_name}' built with {len(index.documents)} documents")

    # 6. Fixed benchmark.
    test_set = load_or_create_test_set(df, settings)
    known_ids = set(df["paper_id"])
    if any(doc_id not in known_ids for item in test_set for doc_id in item["ground_truth_doc_ids"]):
        # A stale benchmark (built from another snapshot) would make every retrieval a miss.
        print("[5/7] Test set references papers missing from the clean data; rebuilding it")
        test_set = build_test_set(df, paths.eval_testset)
    print(f"[5/7] Test set: {len(test_set)} questions -> {paths.eval_testset}")

    # 7. Evaluate.
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=paths.eval_testset,
        metrics_output_path=paths.baseline_metrics,
        answers_output_path=paths.baseline_answers,
    )
    metrics = bundle.summary
    print(
        f"[6/7] Baseline metrics: hit_rate={metrics['retrieval_hit_rate']:.2f} "
        f"token_f1={metrics['mean_token_f1']:.2f} judge_accuracy={metrics['judge_accuracy']:.2f} "
        f"judge_score={metrics['mean_judge_score']:.2f}"
    )

    # 9. Markdown report.
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "source_mode": source_mode,
        "run_date": run_date.isoformat(),
        "raw_records": len(records),
        "clean_rows": len(df),
        "collection_name": index.collection_name,
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "test_set_size": len(test_set),
    }
    generate_phase1_report(paths.baseline_report, source_summary, metrics, quality, freshness)
    print(f"[7/7] Report written -> {paths.baseline_report}")

    # 10. Optional agent demo; never fail the pipeline because the LLM is unreachable.
    _run_agent_demo(settings, index, test_set[:DEMO_QUESTIONS])


def _run_agent_demo(settings, index: LocalEmbeddingIndex, questions: list[dict[str, Any]]) -> None:
    demo: list[dict[str, Any]] = []
    try:
        from retrieval.agent import build_agent, run_agent_question

        agent = build_agent(settings, index)
        for item in questions:
            demo.append({"question": item["question"], "answer": run_agent_question(agent, item["question"])})
    except Exception as exc:
        demo.append({"error": f"Agent demo skipped: {exc}"})
        print(f"[demo] Agent demo skipped: {exc}")
    write_json(settings.paths.demo_answers, demo)


if __name__ == "__main__":
    main()
