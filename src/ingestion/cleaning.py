from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Build the canonical, deduplicated dataframe used by the pipeline."""
    run_day = _as_utc_day(run_date)
    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id).lower()
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        published = _parse_date(record.published)
        if not paper_id or not title or not summary or published is None:
            continue

        authors = [normalize_whitespace(author) for author in record.authors if normalize_whitespace(author)]
        categories = [normalize_whitespace(category) for category in record.categories if normalize_whitespace(category)]
        authors_joined = compact_join(authors) or "Unknown"
        categories_joined = compact_join(categories) or "Uncategorized"
        published_iso = published.date().isoformat()
        age_days = (run_day - published.date()).days
        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published_iso}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": (
                    normalize_whitespace(record.primary_category)
                    or (categories[0] if categories else "Uncategorized")
                ),
                "published": published_iso,
                "updated": _normalise_optional_date(record.updated),
                "abs_url": normalize_whitespace(record.abs_url),
                "pdf_url": normalize_whitespace(record.pdf_url),
                "comment": normalize_whitespace(record.comment),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    columns = [
        "paper_id", "title", "summary", "authors", "categories", "primary_category", "published", "updated",
        "abs_url", "pdf_url", "comment", "authors_joined", "categories_joined", "summary_chars", "age_days",
        "text_for_embedding",
    ]
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df
    return df.drop_duplicates(subset="paper_id", keep="first").sort_values("paper_id").reset_index(drop=True)


def _as_utc_day(value: datetime):
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date()


def _parse_date(value: str) -> pd.Timestamp | None:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed


def _normalise_optional_date(value: str) -> str:
    parsed = _parse_date(value)
    return parsed.date().isoformat() if parsed is not None else ""
