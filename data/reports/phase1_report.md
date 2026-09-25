# Phase 1 Report - Baseline Pipeline

_Generated at 2026-09-25T09:13:36.499481+00:00_

## Source

| Field | Value |
|---|---|
| source_api | Crossref REST API |
| source_query | agentic retrieval augmented generation large language model |
| source_filter | from-pub-date:2026-03-29,has-abstract:true |
| source_mode | raw_snapshot |
| run_date | 2026-09-25T09:13:16.849764+00:00 |
| raw_records | 24 |
| clean_rows | 24 |
| collection_name | papers-baseline |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| llm_provider | openai |
| test_set_size | 10 |

## Evaluation Metrics

| Metric | Value |
|---|---:|
| samples | 10 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |

Ragas: skipped=Set RUN_RAGAS=1 to enable the slower Ragas pass.

## Data Quality (Great Expectations 1.x)

- Overall success (GX + freshness): **True**
- GX success: **True**

| Expectation | Column | Success |
|---|---|---|
| expect_table_row_count_to_be_between | - | True |
| expect_column_values_to_not_be_null | paper_id | True |
| expect_column_values_to_not_be_null | title | True |
| expect_column_values_to_not_be_null | text_for_embedding | True |
| expect_column_values_to_be_unique | paper_id | True |
| expect_column_value_lengths_to_be_between | summary | True |

## Freshness SLA

| Field | Value |
|---|---|
| latest_published | 2026-09-15 |
| oldest_published | 2026-04-01 |
| stale_rows | 0 |
| total_rows | 24 |
| stale_ratio | 0.0000 |
| freshness_threshold_days | 180 |
| max_stale_ratio | 0.2500 |
| is_fresh | True |
