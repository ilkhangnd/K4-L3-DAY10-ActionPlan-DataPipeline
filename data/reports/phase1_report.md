# Phase 1 Baseline Report

## Run summary

| Field | Value |
| --- | --- |
| Source | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Raw records | 24 |
| Clean records | 24 |
| Chroma collection | papers-baseline |
| Embedding model | sentence-transformers/all-MiniLM-L6-v2 |

## Retrieval and evaluation

| Metric | Value |
| --- | ---: |
| Benchmark samples | 5 |
| Retrieval hit rate | 100.00% |
| Mean token F1 | 0.8370 |
| LLM judge accuracy | 80.00% |
| Mean LLM judge score | 4.4000 / 5 |
| Judge mode | llm |
| Ragas | Set RUN_RAGAS=1 to enable the slower Ragas pass. |

## Data quality gate

| Check | Status |
| --- | --- |
| Great Expectations checks | PASS |
| Overall quality gate | PASS |
| Freshness SLA | PASS |
| Stale records (> 180 days) | 0 / 24 (0.00%) |
| Published-date range | 2026-04-01 to 2026-09-15 |

## Interpretation

The baseline establishes the clean-corpus reference point for later corruption and repair experiments. The stored metrics, answers, quality report, and freshness report are generated from this same run.
