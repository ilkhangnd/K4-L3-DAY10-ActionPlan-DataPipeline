# Corruption & Repair Report

_Generated at 2026-09-25T10:03:40.381227+00:00_

## Three-state comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery |
|---|---:|---:|---:|---:|---:|
| `samples` | 10 | 10 | 10 | +0.0000 | n/a |
| `retrieval_hit_rate` | 1.0000 | 0.8000 | 1.0000 | -0.2000 | 100.00% |
| `mean_token_f1` | 1.0000 | 0.5000 | 1.0000 | -0.5000 | 100.00% |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | -0.5000 | 100.00% |
| `mean_judge_score` | 5 | 3 | 5 | -2.0000 | 100.00% |

## Data observability signals

| Signal | Baseline | Corrupted | Repaired |
|---|---|---|---|
| Great Expectations gate | PASS | FAIL | PASS |
| Freshness SLA | FRESH | STALE | FRESH |
| Stale-row ratio | reference pass | 50.00% | 0.00% |

## Impact analysis

- Corruption caused measurable degradation in: **retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score**.
- Metrics restored to the baseline level: **retrieval_hit_rate, mean_token_f1, judge_accuracy, mean_judge_score**.
- The corrupted GX gate was **triggered**; the repaired gate **passed**.
- The stale-date injection changed freshness to **stale** at 50.00% stale rows. Repair returned it to **fresh**.

## Repair conclusion

The repair reconstructs the canonical dataframe from the preserved raw records, then rebuilds a separate Chroma collection and evaluates it with the unchanged test set. It does not patch corrupted cells in place. This makes repeated repair runs deterministic and prevents duplicated or stale state from leaking forward.

Supporting evidence: `data/results/corruption_log.json`, `data/results/repair_verification.json`, and the state-specific artifacts in `data/quality/` and `data/results/`.
