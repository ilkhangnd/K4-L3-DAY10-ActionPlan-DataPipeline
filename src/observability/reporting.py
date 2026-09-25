from __future__ import annotations

from pathlib import Path
from typing import Any

from core.utils import now_utc, write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline (phase 1) markdown report."""
    lines = [
        "# Phase 1 Report - Baseline Pipeline",
        "",
        f"_Generated at {now_utc().isoformat()}_",
        "",
        "## Source",
        "",
        "| Field | Value |",
        "|---|---|",
        *(f"| {key} | {_fmt(value)} |" for key, value in source_summary.items()),
        "",
        "## Evaluation Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        *(f"| {key} | {_fmt(metrics[key])} |" for key in _SCALAR_METRICS if key in metrics),
        "",
    ]
    ragas = metrics.get("ragas")
    if ragas:
        lines += ["Ragas: " + ", ".join(f"{key}={_fmt(value)}" for key, value in ragas.items()), ""]

    lines += [
        "## Data Quality (Great Expectations 1.x)",
        "",
        f"- Overall success (GX + freshness): **{quality.get('success')}**",
        f"- GX success: **{quality.get('gx_success')}**",
        "",
        "| Expectation | Column | Success |",
        "|---|---|---|",
        *(_expectation_row(result) for result in quality.get("expectations", [])),
        "",
        "## Freshness SLA",
        "",
        "| Field | Value |",
        "|---|---|",
        *(f"| {key} | {_fmt(value)} |" for key, value in freshness.items()),
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


_SCALAR_METRICS = ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|")


def _expectation_row(result: dict[str, Any]) -> str:
    config = result.get("expectation_config", {})
    column = config.get("kwargs", {}).get("column", "-")
    return f"| {config.get('type', '?')} | {column} | {result.get('success')} |"


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
