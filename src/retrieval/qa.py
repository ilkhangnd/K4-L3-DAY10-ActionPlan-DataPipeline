from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]
    retrieved_scores: list[float]
    retrieved_metadatas: list[dict[str, Any]] = field(default_factory=list)


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    is_vietnamese = any(token in lowered for token in ("tác giả", "khi nào", "công bố", "lĩnh vực", "chuyên ngành", "tóm tắt"))
    if any(phrase in lowered for phrase in ("who authored", "list the authors", "ai là tác giả", "tác giả của", "những ai viết")):
        answer = metadata["authors_joined"]
        return f"Tác giả: {answer}" if is_vietnamese else answer
    if any(phrase in lowered for phrase in ("when was", "publication date", "published on", "khi nào", "ngày công bố", "được công bố", "xuất bản")):
        answer = metadata["published"]
        return f"Ngày công bố: {answer}" if is_vietnamese else answer
    if any(phrase in lowered for phrase in ("what categories", "thuộc lĩnh vực", "thuộc chuyên ngành", "lĩnh vực nào", "chuyên ngành nào", "danh mục")):
        answer = metadata["categories_joined"]
        return f"Lĩnh vực: {answer}" if is_vietnamese else answer
    answer = first_sentence(metadata["summary"])
    return f"Tóm tắt: {answer}" if is_vietnamese else answer


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    title_match = re.search(r"[\"'“”‘’]([^\"'“”‘’]+)[\"'“”‘’]", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
        retrieved_scores=[item.score for item in retrieved],
        retrieved_metadatas=[getattr(item, "metadata", {}) or {} for item in retrieved],
    )
