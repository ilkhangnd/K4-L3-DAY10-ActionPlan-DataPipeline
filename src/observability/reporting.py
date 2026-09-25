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
    """Write an evidence-based comparison of all three pipeline states."""
    metric_rows = []
    for key in _SCALAR_METRICS:
        if key not in baseline_metrics:
            continue
        baseline = baseline_metrics[key]
        corrupted = corrupted_metrics.get(key)
        repaired = repaired_metrics.get(key)
        delta = _numeric_delta(corrupted, baseline)
        recovery = _recovery_percent(baseline, corrupted, repaired)
        metric_rows.append(
            f"| `{key}` | {_fmt(baseline)} | {_fmt(corrupted)} | {_fmt(repaired)} "
            f"| {_signed(delta)} | {recovery} |"
        )

    corrupted_gx = bool(corrupted_quality.get("gx_success"))
    repaired_gx = bool(repaired_quality.get("gx_success"))
    corrupted_is_fresh = bool(corrupted_freshness.get("is_fresh"))
    repaired_is_fresh = bool(repaired_freshness.get("is_fresh"))
    degraded_metrics = [
        key for key in ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
        if isinstance(baseline_metrics.get(key), (int, float))
        and isinstance(corrupted_metrics.get(key), (int, float))
        and corrupted_metrics[key] < baseline_metrics[key]
    ]
    recovered_metrics = [
        key for key in degraded_metrics
        if isinstance(repaired_metrics.get(key), (int, float))
        and repaired_metrics[key] >= baseline_metrics[key] - 1e-9
    ]

    lines = [
        "# Corruption & Repair Report",
        "",
        f"_Generated at {now_utc().isoformat()}_",
        "",
        "## Three-state comparison",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery |",
        "|---|---:|---:|---:|---:|---:|",
        *metric_rows,
        "",
        "## Data observability signals",
        "",
        "| Signal | Baseline | Corrupted | Repaired |",
        "|---|---|---|---|",
        f"| Great Expectations gate | PASS | {'PASS' if corrupted_gx else 'FAIL'} | {'PASS' if repaired_gx else 'FAIL'} |",
        f"| Freshness SLA | FRESH | {'FRESH' if corrupted_is_fresh else 'STALE'} | {'FRESH' if repaired_is_fresh else 'STALE'} |",
        f"| Stale-row ratio | reference pass | {_percent(corrupted_freshness.get('stale_ratio'))} | {_percent(repaired_freshness.get('stale_ratio'))} |",
        "",
        "## Impact analysis",
        "",
        f"- Corruption caused measurable degradation in: **{', '.join(degraded_metrics) or 'no scalar metric'}**.",
        f"- Metrics restored to the baseline level: **{', '.join(recovered_metrics) or 'none'}**.",
        f"- The corrupted GX gate was **{'not triggered' if corrupted_gx else 'triggered'}**; "
        f"the repaired gate **{'passed' if repaired_gx else 'still failed'}**.",
        f"- The stale-date injection changed freshness to **{'fresh' if corrupted_is_fresh else 'stale'}** "
        f"at {_percent(corrupted_freshness.get('stale_ratio'))} stale rows. "
        f"Repair returned it to **{'fresh' if repaired_is_fresh else 'stale'}**.",
        "",
        "## Repair conclusion",
        "",
        "The repair reconstructs the canonical dataframe from the preserved raw records, then rebuilds a separate "
        "Chroma collection and evaluates it with the unchanged test set. It does not patch corrupted cells in place. "
        "This makes repeated repair runs deterministic and prevents duplicated or stale state from leaking forward.",
        "",
        "Supporting evidence: `data/results/corruption_log.json`, "
        "`data/results/repair_verification.json`, and the state-specific artifacts in `data/quality/` and `data/results/`.",
        "",
    ]
    write_text(Path(report_path), "\n".join(lines))


def _numeric_delta(value: Any, reference: Any) -> float | None:
    if isinstance(value, (int, float)) and isinstance(reference, (int, float)):
        return float(value) - float(reference)
    return None


def _signed(value: float | None) -> str:
    return "-" if value is None else f"{value:+.4f}"


def _percent(value: Any) -> str:
    return f"{float(value):.2%}" if isinstance(value, (int, float)) else "-"


def _recovery_percent(baseline: Any, corrupted: Any, repaired: Any) -> str:
    if not all(isinstance(value, (int, float)) for value in (baseline, corrupted, repaired)):
        return "-"
    lost = float(baseline) - float(corrupted)
    if abs(lost) < 1e-12:
        return "n/a"
    return f"{((float(repaired) - float(corrupted)) / lost):.2%}"
