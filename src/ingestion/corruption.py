from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


CORRUPTION_SCENARIOS = (
    "drop_latest_records",
    "blank_summary",
    "inject_text_noise",
    "truncate_title",
    "stale_date",
    "duplicate_rows",
)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic corruption scenarios to a clean dataframe.

    The dropped newest records are replaced by duplicate rows at the end. This
    preserves the input row count for an apples-to-apples baseline comparison,
    while still introducing both missing fresh evidence and duplicate IDs.
    """
    _validate_clean_dataframe(df)
    original_rows = len(df)
    corrupted = df.copy(deep=True).reset_index(drop=True)
    drop_count = min(max(1, ceil(original_rows * 0.2)), original_rows - 1)

    # 1. Remove the newest papers first: this models a failed incremental sync.
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    latest_indices = published.sort_values(ascending=False).head(drop_count).index
    dropped_ids = corrupted.loc[latest_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=latest_indices).reset_index(drop=True)

    # 2. Blank source summaries. These rows will fail the length expectation.
    blank_indices = corrupted.index[: min(2, len(corrupted))]
    blank_ids = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[blank_indices, "summary"] = ""
    corrupted.loc[blank_indices, "summary_chars"] = 0

    # 3. Shorten titles to an unusable fragment (<10 characters).
    title_indices = corrupted.index[2 : min(4, len(corrupted))]
    title_ids = corrupted.loc[title_indices, "paper_id"].astype(str).tolist()
    corrupted.loc[title_indices, "title"] = corrupted.loc[title_indices, "title"].map(
        lambda value: str(value)[:8]
    )

    # 4. Make more than 25% of the final corpus stale by moving dates back five
    # years. ``age_days`` is updated so the Freshness SLA sees the same state.
    stale_count = min(max(1, ceil(original_rows * 0.30)), len(corrupted))
    stale_indices = corrupted.index[-stale_count:]
    stale_ids = corrupted.loc[stale_indices, "paper_id"].astype(str).tolist()
    stale_date = (datetime.now(UTC).date() - timedelta(days=5 * 365)).isoformat()
    corrupted.loc[stale_indices, "published"] = stale_date
    corrupted.loc[stale_indices, "age_days"] = 5 * 365

    # Rebuild the structured embedding context after title/date/summary edits.
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)

    # 5. Inject non-semantic characters into the vector payload only.
    noise_indices = corrupted.index[4 : min(6, len(corrupted))]
    noise_ids = corrupted.loc[noise_indices, "paper_id"].astype(str).tolist()
    noise = "\n[CORRUPTION_NOISE: ###@@@%%% INVALID_VECTOR_PAYLOAD ###@@@%%%]"
    corrupted.loc[noise_indices, "text_for_embedding"] = (
        corrupted.loc[noise_indices, "text_for_embedding"].astype(str) + noise
    )

    # 6. Duplicate enough remaining rows to offset the initial dropped rows.
    duplicate_rows = corrupted.iloc[:drop_count].copy(deep=True)
    duplicate_ids = duplicate_rows["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    log = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_rows": original_rows,
        "output_rows": len(corrupted),
        "scenario_count": len(CORRUPTION_SCENARIOS),
        "scenarios": [
            {
                "name": "drop_latest_records",
                "description": "Dropped the newest 20% of papers to simulate a failed fresh-data sync.",
                "affected_paper_ids": dropped_ids,
                "rows_affected": len(dropped_ids),
            },
            {
                "name": "blank_summary",
                "description": "Blanked summaries while retaining their record metadata.",
                "affected_paper_ids": blank_ids,
                "rows_affected": len(blank_ids),
            },
            {
                "name": "inject_text_noise",
                "description": "Injected meaningless noise into text_for_embedding.",
                "affected_paper_ids": noise_ids,
                "rows_affected": len(noise_ids),
            },
            {
                "name": "truncate_title",
                "description": "Truncated titles to eight characters.",
                "affected_paper_ids": title_ids,
                "rows_affected": len(title_ids),
            },
            {
                "name": "stale_date",
                "description": f"Moved publication dates to {stale_date} (five years old).",
                "affected_paper_ids": stale_ids,
                "rows_affected": len(stale_ids),
            },
            {
                "name": "duplicate_rows",
                "description": "Duplicated rows to restore the original row count and create duplicate paper_id values.",
                "affected_paper_ids": duplicate_ids,
                "rows_affected": len(duplicate_ids),
            },
        ],
    }
    write_json(Path(output_log_path), log)
    return corrupted


def _validate_clean_dataframe(df: pd.DataFrame) -> None:
    required_columns = {
        "paper_id", "title", "summary", "authors_joined", "published", "categories_joined",
        "summary_chars", "age_days", "text_for_embedding",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Corruption requires columns: {', '.join(missing_columns)}")
    if len(df) < 2:
        raise ValueError("At least two clean rows are required for the corruption scenarios.")


def _embedding_text(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )
