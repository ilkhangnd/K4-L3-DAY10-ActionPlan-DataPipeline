# Corruption, Repair & Comparison Report

## Three-state comparison

| Metric | Baseline (clean) | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Data Quality Gate | PASS | FAIL | PASS |
| Great Expectations | PASS | FAIL | PASS |
| Freshness SLA | PASS | FAIL | PASS |
| Stale records | 0 / 24 (0.00%) | 8 / 24 (33.33%) | 0 / 24 (0.00%) |
| Retrieval hit rate | 100.00% | 80.00% | 100.00% |
| Mean token F1 | 0.7403 | 0.5403 | 0.7403 |
| Judge accuracy | 70.00% | 50.00% | 70.00% |
| Mean judge score | 3.8000 | 3.0000 | 3.8000 |

## Impact analysis

- Retrieval hit-rate change after corruption: -0.2000 (-20.00 pp).
- Token-F1 change after corruption: -0.2000 (-20.00 pp).
- The corrupted state intentionally contains dropped recent records, blank summaries, noisy embedding text, truncated titles, stale dates, and duplicate paper IDs. The failed Quality Gate is the early warning that prevents a silent production failure.
- The repaired state is rebuilt idempotently from `data/raw/crossref_records.json`, not patched in place. Its metrics should return to the clean baseline when the raw snapshot is unchanged.

## Evaluation notes

| State | Judge mode | Ragas |
| --- | --- | --- |
| Baseline | fallback_heuristic | Set RUN_RAGAS=1 to enable the slower Ragas pass. |
| Corrupted | fallback_heuristic | Set RUN_RAGAS=1 to enable the slower Ragas pass. |
| Repaired | fallback_heuristic | Set RUN_RAGAS=1 to enable the slower Ragas pass. |
