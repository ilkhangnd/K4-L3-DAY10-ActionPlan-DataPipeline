from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


BENCHMARK_SIZE = 10


@dataclass(frozen=True)
class TestSet:
    """A small, reproducible benchmark and its in-memory samples."""

    samples: list[dict[str, Any]]

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create ten deterministic, source-grounded evaluation questions.

    The 10 samples are balanced across summary, authors, date, category, and
    multi-hop questions. All answers and cited DOI(s) come from the clean
    corpus so that evaluation remains reproducible after each rebuild.
    """
    required_columns = {
        "paper_id", "title", "summary", "authors_joined", "published", "categories_joined",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(f"Test-set generation requires columns: {', '.join(missing_columns)}")
    if len(df) < 12:
        raise ValueError("At least 12 clean documents are required to build the 10-question benchmark.")

    records = df.sort_values("paper_id").reset_index(drop=True).to_dict(orient="records")
    summary_a, authors_a, date_a, category_a, hop_left_a, hop_right_a = records[:6]
    summary_b, authors_b, date_b, category_b, hop_left_b, hop_right_b = records[6:12]
    samples = [
        _sample("eval_001", "summary", f"What is the summary of the paper '{summary_a['title']}'?", first_sentence(str(summary_a["summary"])), [str(summary_a["paper_id"])]),
        _sample("eval_002", "summary", f"Summarize the main research contribution of '{summary_b['title']}'.", first_sentence(str(summary_b["summary"])), [str(summary_b["paper_id"])]),
        _sample("eval_003", "authors", f"Who authored the paper '{authors_a['title']}'?", str(authors_a["authors_joined"]), [str(authors_a["paper_id"])]),
        _sample("eval_004", "authors", f"List the authors of the study '{authors_b['title']}'.", str(authors_b["authors_joined"]), [str(authors_b["paper_id"])]),
        _sample("eval_005", "date", f"When was the paper '{date_a['title']}' published?", str(date_a["published"]), [str(date_a["paper_id"])]),
        _sample("eval_006", "date", f"What is the publication date of '{date_b['title']}'?", str(date_b["published"]), [str(date_b["paper_id"])]),
        _sample("eval_007", "category", f"What categories does the paper '{category_a['title']}' belong to?", str(category_a["categories_joined"]), [str(category_a["paper_id"])]),
        _sample("eval_008", "category", f"Which research category is assigned to '{category_b['title']}'?", str(category_b["categories_joined"]), [str(category_b["paper_id"])]),
        _sample(
            "eval_009", "multi_hop",
            f"How do '{hop_left_a['title']}' and '{hop_right_a['title']}' connect across their research areas?",
            f"{hop_left_a['title']} is categorized as {hop_left_a['categories_joined']}; {hop_right_a['title']} is categorized as {hop_right_a['categories_joined']}.",
            [str(hop_left_a["paper_id"]), str(hop_right_a["paper_id"])],
        ),
        _sample(
            "eval_010", "multi_hop",
            f"Compare the research areas of '{hop_left_b['title']}' and '{hop_right_b['title']}'.",
            f"{hop_left_b['title']} is categorized as {hop_left_b['categories_joined']}; {hop_right_b['title']} is categorized as {hop_right_b['categories_joined']}.",
            [str(hop_left_b["paper_id"]), str(hop_right_b["paper_id"])],
        ),
    ]
    write_json(Path(output_path), samples)
    return samples


def load_or_create_test_set(df: pd.DataFrame, output_path, refresh: bool = False) -> TestSet:
    """Load a valid 10-question benchmark or recreate an outdated artifact."""
    path = Path(output_path)
    if path.exists() and not refresh:
        samples = read_json(path)
        if not isinstance(samples, list):
            raise ValueError(f"Expected a list of samples in {path}")
        required_types = {"summary", "authors", "date", "category", "multi_hop"}
        actual_types = {str(sample.get("type", "")) for sample in samples}
        if len(samples) == BENCHMARK_SIZE and required_types.issubset(actual_types):
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
