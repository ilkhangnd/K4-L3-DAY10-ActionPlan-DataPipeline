# Architecture & Method Notes

## One-minute presentation narrative

This project builds a retrieval-augmented generation pipeline for scholarly papers. The key engineering point is that data quality is monitored before the corpus is trusted by the RAG system. We preserve raw Crossref records, clean and enrich them, validate them with Great Expectations 1.x, build a ChromaDB vector index using MiniLM embeddings, and evaluate retrieval/answer quality with a fixed benchmark.

To prove why the quality gate matters, we inject six controlled faults: records are dropped, summaries blanked, embedding text polluted, titles truncated, dates made stale, and DOI rows duplicated. The system may still return an answer—this is the silent failure—but retrieval metrics fall and the quality/freshness checks fail. Repair does not patch corrupt records. It rebuilds a separate dataset from the preserved raw artifact, making recovery repeatable and auditable.

## Architecture flow

```text
Crossref API / offline snapshot
        ↓
Raw artifacts (lineage preserved)
        ↓
Cleaning + age_days + text_for_embedding
        ↓
Great Expectations 1.x + Freshness SLA
        ↓
MiniLM embeddings → ChromaDB collections
        ↓
Retrieval QA + Benchmark evaluation
        ↓
Baseline ↔ Corrupted ↔ Repaired comparison
```

## Methods applied

- **Data lineage:** raw API response and normalized raw records are retained.
- **Data quality gate:** row-count, non-null, unique DOI, summary length, and freshness checks.
- **Semantic retrieval:** `sentence-transformers/all-MiniLM-L6-v2` embeddings stored in ChromaDB with cosine distance.
- **Controlled fault injection:** deterministic corruption makes experiments repeatable.
- **Idempotent repair:** re-clean raw records into a dedicated repaired artifact; baseline is never overwritten.
- **Evidence-based evaluation:** retrieval hit rate, Token F1, judge score, and comparison reports.
