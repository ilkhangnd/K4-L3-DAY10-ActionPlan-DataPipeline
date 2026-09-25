from __future__ import annotations

from datetime import timedelta
from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import now_utc, write_json


CORRUPTION_SCENARIOS = (
    "drop_latest_records",
    "blank_summary",
    "inject_noise",
    "truncate_title",
    "stale_date",
    "duplicate_rows",
)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Inject six deterministic production-like faults into a clean dataframe.

    The deterministic row selection makes baseline/corrupted/repaired runs
    directly comparable.  The input dataframe is never mutated.
    """
    required = {
        "paper_id", "title", "summary", "published", "age_days",
        "authors_joined", "categories_joined", "text_for_embedding",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Corruption suite requires columns: {', '.join(missing)}")
    if len(df) < 10:
        raise ValueError("Corruption suite requires at least 10 clean rows.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    original_rows = len(corrupted)
    scenarios: list[dict] = []

    # 1. Simulate an ingestion outage by losing the newest 20% of records.
    published = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_count = max(1, ceil(original_rows * 0.20))
    drop_indices = published.sort_values(ascending=False, na_position="last").index[:drop_count]
    dropped_ids = corrupted.loc[drop_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)
    scenarios.append(
        _event("drop_latest_records", dropped_ids, {"fraction": 0.20, "rows_removed": drop_count})
    )

    # Remaining mutations deliberately touch stable, low-index records.  The
    # benchmark uses stable paper IDs, so this exposes silent RAG degradation.
    blank_indices = _positions(corrupted, 0, 3)
    corrupted.loc[blank_indices, "summary"] = ""
    scenarios.append(_event("blank_summary", _ids(corrupted, blank_indices), {"replacement": ""}))

    noise_indices = _positions(corrupted, 3, 3)
    noise_prefix = "CORRUPTED TOKEN STREAM !!! 9f4a zzz invalid payload. "
    corrupted.loc[noise_indices, "summary"] = (
        noise_prefix + corrupted.loc[noise_indices, "summary"].astype(str)
    )
    scenarios.append(
        _event("inject_noise", _ids(corrupted, noise_indices), {"prefix": noise_prefix.strip()})
    )

    title_indices = _positions(corrupted, 6, 3)
    corrupted.loc[title_indices, "title"] = (
        corrupted.loc[title_indices, "title"].astype(str).str.slice(0, 7)
    )
    scenarios.append(
        _event("truncate_title", _ids(corrupted, title_indices), {"maximum_characters": 7})
    )

    stale_indices = _positions(corrupted, 0, max(7, ceil(len(corrupted) * 0.40)))
    stale_dates = pd.to_datetime(corrupted.loc[stale_indices, "published"], errors="coerce")
    corrupted.loc[stale_indices, "published"] = stale_dates.map(
        lambda value: (value - timedelta(days=365)).date().isoformat() if not pd.isna(value) else "1900-01-01"
    )
    ages = pd.to_numeric(corrupted.loc[stale_indices, "age_days"], errors="coerce").fillna(0)
    corrupted.loc[stale_indices, "age_days"] = (ages + 365).astype(int)
    scenarios.append(
        _event("stale_date", _ids(corrupted, stale_indices), {"days_shifted_back": 365})
    )

    # Rebuild all derived fields after the cell-level mutations.
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)

    duplicate_indices = _positions(corrupted, 0, 3)
    duplicates = corrupted.loc[duplicate_indices].copy(deep=True)
    duplicate_ids = duplicates["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)
    scenarios.append(_event("duplicate_rows", duplicate_ids, {"rows_added": len(duplicates)}))

    write_json(
        Path(output_log_path),
        {
            "generated_at": now_utc().isoformat(),
            "strategy": "deterministic",
            "original_rows": original_rows,
            "final_rows": len(corrupted),
            "scenario_count": len(scenarios),
            "scenarios": scenarios,
        },
    )
    return corrupted.reset_index(drop=True)


def _positions(df: pd.DataFrame, start: int, count: int) -> list[int]:
    return list(df.index[start : min(start + count, len(df))])


def _ids(df: pd.DataFrame, indices: list[int]) -> list[str]:
    return df.loc[indices, "paper_id"].astype(str).tolist()


def _event(name: str, paper_ids: list[str], parameters: dict) -> dict:
    return {
        "corruption_type": name,
        "affected_count": len(paper_ids),
        "paper_ids": paper_ids,
        "parameters": parameters,
    }


def _embedding_text(row: pd.Series) -> str:
    return (
        f"Title: {row['title']}\n"
        f"Authors: {row['authors_joined']}\n"
        f"Published: {row['published']}\n"
        f"Categories: {row['categories_joined']}\n"
        f"Summary: {row['summary']}"
    )
