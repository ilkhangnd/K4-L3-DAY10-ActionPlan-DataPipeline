from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write a concise, self-contained report for the clean baseline run."""
    report = f"""# Phase 1 Baseline Report

## Run summary

| Field | Value |
| --- | --- |
| Source | {source_summary.get('source', 'N/A')} |
| Query | {source_summary.get('query', 'N/A')} |
| Raw records | {source_summary.get('raw_records', 0)} |
| Clean records | {source_summary.get('clean_records', 0)} |
| Chroma collection | {source_summary.get('collection_name', 'N/A')} |
| Embedding model | {source_summary.get('embedding_model', 'N/A')} |

## Retrieval and evaluation

| Metric | Value |
| --- | ---: |
| Benchmark samples | {metrics.get('samples', 0)} |
| Retrieval hit rate | {_percent(metrics.get('retrieval_hit_rate'))} |
| Mean token F1 | {_number(metrics.get('mean_token_f1'))} |
| LLM judge accuracy | {_percent(metrics.get('judge_accuracy'))} |
| Mean LLM judge score | {_number(metrics.get('mean_judge_score'))} / 5 |
| Judge mode | {metrics.get('judge_mode', 'N/A')} |
| Ragas | {_ragas_status(metrics.get('ragas'))} |

## Data quality gate

| Check | Status |
| --- | --- |
| Great Expectations checks | {'PASS' if quality.get('gx_success') else 'FAIL'} |
| Overall quality gate | {'PASS' if quality.get('success') else 'FAIL'} |
| Freshness SLA | {'PASS' if freshness.get('is_fresh') else 'WARNING'} |
| Stale records (> {freshness.get('freshness_threshold_days', 180)} days) | {freshness.get('stale_rows', 0)} / {freshness.get('total_rows', 0)} ({_percent(freshness.get('stale_ratio'))}) |
| Published-date range | {freshness.get('oldest_published', 'N/A')} to {freshness.get('latest_published', 'N/A')} |

## Interpretation

The baseline establishes the clean-corpus reference point for later corruption and repair experiments. The stored metrics, answers, quality report, and freshness report are generated from this same run.
"""
    write_text(report_path, report)


def _number(value: Any) -> str:
    return f"{float(value):.4f}" if isinstance(value, (int, float)) else "N/A"


def _percent(value: Any) -> str:
    return f"{float(value) * 100:.2f}%" if isinstance(value, (int, float)) else "N/A"


def _ragas_status(value: Any) -> str:
    if isinstance(value, dict) and "skipped" in value:
        return str(value["skipped"])
    if isinstance(value, dict) and "error" in value:
        return f"Not available ({value['error']})"
    return "Completed"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Write an evidence-backed comparison of baseline, failure, and repair."""
    baseline_quality = baseline_quality or {}
    baseline_freshness = baseline_freshness or {}
    report = f"""# Corruption, Repair & Comparison Report

## Three-state comparison

| Metric | Baseline (clean) | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Data Quality Gate | {_status(baseline_quality.get('success'))} | {_status(corrupted_quality.get('success'))} | {_status(repaired_quality.get('success'))} |
| Great Expectations | {_status(baseline_quality.get('gx_success'))} | {_status(corrupted_quality.get('gx_success'))} | {_status(repaired_quality.get('gx_success'))} |
| Freshness SLA | {_fresh_status(baseline_freshness)} | {_fresh_status(corrupted_freshness)} | {_fresh_status(repaired_freshness)} |
| Stale records | {_stale_summary(baseline_freshness)} | {_stale_summary(corrupted_freshness)} | {_stale_summary(repaired_freshness)} |
| Retrieval hit rate | {_percent(baseline_metrics.get('retrieval_hit_rate'))} | {_percent(corrupted_metrics.get('retrieval_hit_rate'))} | {_percent(repaired_metrics.get('retrieval_hit_rate'))} |
| Mean token F1 | {_number(baseline_metrics.get('mean_token_f1'))} | {_number(corrupted_metrics.get('mean_token_f1'))} | {_number(repaired_metrics.get('mean_token_f1'))} |
| Judge accuracy | {_percent(baseline_metrics.get('judge_accuracy'))} | {_percent(corrupted_metrics.get('judge_accuracy'))} | {_percent(repaired_metrics.get('judge_accuracy'))} |
| Mean judge score | {_number(baseline_metrics.get('mean_judge_score'))} | {_number(corrupted_metrics.get('mean_judge_score'))} | {_number(repaired_metrics.get('mean_judge_score'))} |

## Impact analysis

- Retrieval hit-rate change after corruption: {_delta(baseline_metrics.get('retrieval_hit_rate'), corrupted_metrics.get('retrieval_hit_rate'))}.
- Token-F1 change after corruption: {_delta(baseline_metrics.get('mean_token_f1'), corrupted_metrics.get('mean_token_f1'))}.
- The corrupted state intentionally contains dropped recent records, blank summaries, noisy embedding text, truncated titles, stale dates, and duplicate paper IDs. The failed Quality Gate is the early warning that prevents a silent production failure.
- The repaired state is rebuilt idempotently from `data/raw/crossref_records.json`, not patched in place. Its metrics should return to the clean baseline when the raw snapshot is unchanged.

## Evaluation notes

| State | Judge mode | Ragas |
| --- | --- | --- |
| Baseline | {baseline_metrics.get('judge_mode', 'N/A')} | {_ragas_status(baseline_metrics.get('ragas'))} |
| Corrupted | {corrupted_metrics.get('judge_mode', 'N/A')} | {_ragas_status(corrupted_metrics.get('ragas'))} |
| Repaired | {repaired_metrics.get('judge_mode', 'N/A')} | {_ragas_status(repaired_metrics.get('ragas'))} |
"""
    write_text(report_path, report)


def _status(value: Any) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "N/A"


def _fresh_status(freshness: dict[str, Any]) -> str:
    return "PASS" if freshness.get("is_fresh") else "FAIL"


def _stale_summary(freshness: dict[str, Any]) -> str:
    total = freshness.get("total_rows", 0)
    return f"{freshness.get('stale_rows', 0)} / {total} ({_percent(freshness.get('stale_ratio'))})"


def _delta(baseline: Any, changed: Any) -> str:
    if not isinstance(baseline, (int, float)) or not isinstance(changed, (int, float)):
        return "N/A"
    difference = float(changed) - float(baseline)
    return f"{difference:+.4f} ({difference * 100:+.2f} pp)"
