from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


@dataclass(frozen=True)
class TestSet:
    """A small, reproducible benchmark and its in-memory samples."""

    samples: list[dict[str, Any]]

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create five deterministic, source-grounded evaluation questions.

    Questions are generated from the cleaned corpus rather than hard-coded
    content, so their answers and cited DOI(s) always remain aligned.
    """
    required_columns = {
        "paper_id", "title", "summary", "authors_joined", "published", "categories_joined",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Test-set generation requires columns: {', '.join(missing_columns)}")
    if len(df) < 6:
        raise ValueError("At least 6 clean documents are required to build the benchmark test set.")

    records = df.sort_values("paper_id").reset_index(drop=True).to_dict(orient="records")
    summary_doc, authors_doc, date_doc, category_doc, hop_left, hop_right = records[:6]
    samples = [
        _sample(
            "eval_001",
            "summary",
            f"What is the summary of the paper '{summary_doc['title']}'?",
            first_sentence(str(summary_doc["summary"])),
            [str(summary_doc["paper_id"])],
        ),
        _sample(
            "eval_002",
            "authors",
            f"Who authored the paper '{authors_doc['title']}'?",
            str(authors_doc["authors_joined"]),
            [str(authors_doc["paper_id"])],
        ),
        _sample(
            "eval_003",
            "date",
            f"When was the paper '{date_doc['title']}' published?",
            str(date_doc["published"]),
            [str(date_doc["paper_id"])],
        ),
        _sample(
            "eval_004",
            "category",
            f"What categories does the paper '{category_doc['title']}' belong to?",
            str(category_doc["categories_joined"]),
            [str(category_doc["paper_id"])],
        ),
        _sample(
            "eval_005",
            "multi_hop",
            (
                f"How do '{hop_left['title']}' and '{hop_right['title']}' connect "
                "across their research areas?"
            ),
            (
                f"{hop_left['title']} is categorized as {hop_left['categories_joined']}; "
                f"{hop_right['title']} is categorized as {hop_right['categories_joined']}."
            ),
            [str(hop_left["paper_id"]), str(hop_right["paper_id"])],
        ),
    ]
    write_json(Path(output_path), samples)
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path, refresh: bool = False) -> TestSet:
    """Load an existing benchmark, or create it once when it does not exist."""
    path = Path(output_path)
    if path.exists() and not refresh:
        samples = read_json(path)
        if not isinstance(samples, list):
            raise ValueError(f"Expected a list of samples in {path}")
        return TestSet(samples=samples)
    return TestSet(samples=build_test_set(df, path))


def _sample(
    sample_id: str,
    question_type: str,
    question: str,
    ground_truth: str,
    ground_truth_doc_ids: list[str],
) -> dict[str, Any]:
    # ``type`` is required by this checkpoint; ``question_type`` keeps the
    # existing evaluation pipeline compatible with the generated artifact.
    return {
        "id": sample_id,
        "type": question_type,
        "question_type": question_type,
        "question": question,
        "ground_truth": ground_truth,
        "ground_truth_doc_ids": ground_truth_doc_ids,
    }
