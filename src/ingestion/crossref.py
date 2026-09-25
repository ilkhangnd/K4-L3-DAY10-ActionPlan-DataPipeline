from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import html
import json
from pathlib import Path
import re

import requests

from core.config import Settings
from core.utils import ensure_parent, normalize_whitespace


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Convert a Crossref work-list response into normalized paper records."""
    items = payload.get("message", {}).get("items", [])
    if not isinstance(items, list):
        return []

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = _normalize_doi(item.get("DOI", ""))
        title = _first_text(item.get("title"))
        summary = _clean_markup(item.get("abstract", ""))
        if not paper_id or not title or not summary:
            continue

        authors = _authors(item.get("author", []))
        categories = _text_list(item.get("subject", []))
        published = _crossref_date(item, ("published", "published-print", "published-online", "issued"))
        updated = _crossref_date(item, ("updated", "created", "deposited")) or published
        url = normalize_whitespace(str(item.get("URL") or f"https://doi.org/{paper_id}"))
        links = item.get("link", [])
        pdf_url = next(
            (
                normalize_whitespace(str(link.get("URL", "")))
                for link in links
                if isinstance(link, dict)
                and "pdf" in normalize_whitespace(str(link.get("content-type", ""))).lower()
                and link.get("URL")
            ),
            url,
        )

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0] if categories else "Uncategorized",
                published=published,
                updated=updated,
                abs_url=url,
                pdf_url=pdf_url,
                comment=f"Crossref record {paper_id}",
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records, falling back to the committed snapshot when offline.

    The snapshot is intentionally left untouched when the remote service is
    unavailable, so a failed refresh never destroys the lab's reproducible
    input data.
    """
    params = {
        "query.bibliographic": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,published-print,published-online,issued,created,URL,link",
    }
    payload: dict | None = None
    for _attempt in range(2):
        try:
            response = requests.get(
                "https://api.crossref.org/works",
                params=params,
                headers={"User-Agent": "day10-data-observability-lab/0.1 (educational use)"},
                timeout=12,
            )
            # 429/503 and all other HTTP errors use the local rescue snapshot.
            response.raise_for_status()
            candidate = response.json()
            if isinstance(candidate, dict):
                payload = candidate
                break
        except (requests.RequestException, ValueError):
            continue

    if payload is None:
        payload = _read_snapshot(settings.paths.raw_api_response)
    else:
        ensure_parent(settings.paths.raw_api_response)
        settings.paths.raw_api_response.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    records = parse_crossref_payload(payload)
    ensure_parent(settings.paths.raw_records_json)
    settings.paths.raw_records_json.write_text(
        json.dumps([asdict(record) for record in records], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load the normalized raw-record artifact into ``PaperRecord`` objects."""
    raw_records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_records, list):
        raise ValueError(f"Expected a list of records in {path}")

    fields = set(PaperRecord.__dataclass_fields__)
    records: list[PaperRecord] = []
    for raw_record in raw_records:
        if not isinstance(raw_record, dict):
            continue
        values = {name: raw_record.get(name) for name in fields}
        values["paper_id"] = _normalize_doi(values.get("paper_id", ""))
        values["title"] = normalize_whitespace(str(values.get("title") or ""))
        values["summary"] = _clean_markup(values.get("summary", ""))
        values["authors"] = _text_list(values.get("authors", []))
        values["categories"] = _text_list(values.get("categories", []))
        values["primary_category"] = normalize_whitespace(
            str(values.get("primary_category") or (values["categories"][0] if values["categories"] else "Uncategorized"))
        )
        values["published"] = normalize_whitespace(str(values.get("published") or ""))
        values["updated"] = normalize_whitespace(str(values.get("updated") or values["published"]))
        values["abs_url"] = normalize_whitespace(str(values.get("abs_url") or ""))
        values["pdf_url"] = normalize_whitespace(str(values.get("pdf_url") or values["abs_url"]))
        values["comment"] = normalize_whitespace(str(values.get("comment") or ""))
        if values["paper_id"] and values["title"] and values["summary"]:
            records.append(PaperRecord(**values))
    return records


def _read_snapshot(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Crossref is unavailable and the local snapshot could not be read.") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in snapshot {path}")
    return payload


def _normalize_doi(value: object) -> str:
    doi = normalize_whitespace(str(value or "")).lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi.rstrip(".,;)")


def _clean_markup(value: object) -> str:
    text = html.unescape(str(value or ""))
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", text))


def _first_text(value: object) -> str:
    if isinstance(value, list):
        value = next((entry for entry in value if entry), "")
    return _clean_markup(value)


def _text_list(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    return [cleaned for entry in values if (cleaned := normalize_whitespace(str(entry or "")))]


def _authors(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    authors: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = normalize_whitespace(" ".join(str(author.get(part, "") or "") for part in ("given", "family")))
        if name:
            authors.append(name)
    return authors


def _crossref_date(item: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        date_time = value.get("date-time")
        if date_time:
            return normalize_whitespace(str(date_time))[:10]
        date_parts = value.get("date-parts")
        if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list) and date_parts[0]:
            parts = date_parts[0]
            try:
                year = int(parts[0])
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                return date(year, month, day).isoformat()
            except (TypeError, ValueError):
                continue
    return ""
