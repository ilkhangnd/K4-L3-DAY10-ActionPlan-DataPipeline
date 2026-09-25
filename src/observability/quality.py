from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import great_expectations as gx
import pandas as pd
from great_expectations.expectations import (
    ExpectColumnValueLengthsToBeBetween,
    ExpectColumnValuesToBeUnique,
    ExpectColumnValuesToNotBeNull,
    ExpectTableRowCountToBeBetween,
)

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run the GX 1.x quality gate and persist an inspectable JSON report."""
    required_columns = {"paper_id", "title", "text_for_embedding", "summary", "age_days", "published"}
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Quality gate requires columns: {', '.join(missing_columns)}")

    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name="papers_source")
    data_asset = data_source.add_dataframe_asset(name="papers_asset")
    batch_definition = data_asset.add_batch_definition_whole_dataframe("papers_batch")
    batch = batch_definition.get_batch(batch_parameters={"dataframe": df})

    expectations = [
        ExpectTableRowCountToBeBetween(min_value=5, max_value=5000),
        *(ExpectColumnValuesToNotBeNull(column=column) for column in ("paper_id", "title", "text_for_embedding")),
        ExpectColumnValuesToBeUnique(column="paper_id"),
        ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results = [batch.validate(expectation).to_json_dict() for expectation in expectations]
    gx_success = all(result["success"] for result in results)

    freshness = _freshness_payload(df, settings)
    report = {
        "report_name": report_name,
        "generated_at": datetime.now(UTC).isoformat(),
        "success": gx_success and freshness["is_fresh"],
        "gx_success": gx_success,
        "freshness": freshness,
        "expectations": results,
    }
    write_json(_quality_report_path(settings, report_name), report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarise the freshness SLA independently of the GX expectation results."""
    payload = _freshness_payload(df, settings)
    write_json(report_path, payload)
    return payload


def _quality_report_path(settings: Settings, report_name: str):
    if report_name == "baseline":
        return settings.paths.baseline_quality_report
    if report_name == "corrupted":
        return settings.paths.corrupted_quality_report
    if report_name == "repaired":
        return settings.paths.repaired_quality_report
    return settings.paths.quality_dir / f"{report_name}_quality_report.json"


def _freshness_payload(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    if "published" not in df or "age_days" not in df:
        raise ValueError("Freshness check requires 'published' and 'age_days' columns.")

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    ages = pd.to_numeric(df["age_days"], errors="coerce")
    total_rows = len(df)
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    valid_dates = published.dropna()
    return {
        "latest_published": valid_dates.max().date().isoformat() if not valid_dates.empty else None,
        "oldest_published": valid_dates.min().date().isoformat() if not valid_dates.empty else None,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "max_stale_ratio": 0.25,
        "is_fresh": bool(total_rows and stale_ratio <= 0.25),
    }
