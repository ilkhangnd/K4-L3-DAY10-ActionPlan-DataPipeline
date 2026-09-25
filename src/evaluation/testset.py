from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import first_sentence, read_json, write_json


QUESTION_TYPES = ("summary", "authors", "date", "categories")
REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "published",
    "categories_joined",
}


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create a deterministic 10-question benchmark from cleaned papers.

    Questions quote the paper title so the retrieval layer can both perform
    semantic search and verify the expected document by its stable paper ID.
    The same deterministic set can therefore be reused for baseline,
    corrupted, and repaired evaluations.
    """
    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Test-set builder requires columns: {', '.join(missing_columns)}")

    candidates = df.dropna(subset=list(REQUIRED_COLUMNS)).copy()
    candidates = candidates.drop_duplicates(subset="paper_id", keep="first")
    candidates = candidates.sort_values("paper_id").reset_index(drop=True)
    if len(candidates) < 10:
        raise ValueError(f"At least 10 unique clean papers are required; received {len(candidates)}.")

    test_set: list[dict[str, Any]] = []
    for index, (_, paper) in enumerate(candidates.iloc[:10].iterrows(), start=1):
        question_type = QUESTION_TYPES[(index - 1) % len(QUESTION_TYPES)]
        title = str(paper["title"])
        if question_type == "summary":
            question = f"What is the main finding of the paper '{title}'?"
            ground_truth = first_sentence(str(paper["summary"]))
        elif question_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(paper["authors_joined"])
        elif question_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(paper["published"])
        else:
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(paper["categories_joined"])

        if not ground_truth.strip():
            raise ValueError(f"Paper {paper['paper_id']} has no ground truth for {question_type}.")
        test_set.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [str(paper["paper_id"])],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set


def load_or_create_test_set(df: pd.DataFrame, settings: Settings) -> list[dict[str, Any]]:
    """Load the fixed benchmark, rebuilding it only when requested or absent."""
    path = settings.paths.eval_testset
    if settings.refresh_test_set or not path.exists():
        return build_test_set(df, path)

    test_set = read_json(path)
    if not isinstance(test_set, list) or not test_set:
        raise ValueError(f"Expected a non-empty test-set list in {path}.")
    required_keys = {"id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"}
    for index, item in enumerate(test_set, start=1):
        if not isinstance(item, dict) or not required_keys.issubset(item):
            raise ValueError(f"Invalid test-set item at position {index} in {path}.")
    return test_set
