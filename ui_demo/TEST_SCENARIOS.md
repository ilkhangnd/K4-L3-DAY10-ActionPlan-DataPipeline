# UI Demo Test Scenarios

Run the two pipeline commands before presenting:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Then open the **Test scenarios** tab in the UI. It evaluates the same conditions below against the latest files under `data/`.

| ID | Scenario | Action | Expected result |
| --- | --- | --- | --- |
| T01 | Clean baseline | Select **Baseline (clean)**. | Quality Gate and Freshness SLA are `PASS`; Retrieval Hit Rate is high (target >=80%) and Token F1 is high (target >=0.70). |
| T02 | Corruption coverage | Open `data/results/corruption_log.json`. | Exactly six names appear: drop latest, blank summary, inject noise, truncate title, stale date, duplicate rows. |
| T03 | GX detection | Select **Corrupted** in Observability. | Data Quality Gate is `FAIL` because summaries are blank and DOI values are duplicated. |
| T04 | Freshness violation | Select **Corrupted** in Observability. | Freshness is `FAIL`; stale ratio is greater than 25%. |
| T05 | Silent failure | Ask the same factual question in Baseline and Corrupted chat. | Corrupted state can still answer, but its retrieval hit rate and Token F1 are lower than Baseline. |
| T06 | Idempotent repair | Select **Repaired**. | Quality and freshness return to `PASS`; Retrieval Hit Rate and Token F1 return to the Baseline value. |

## Suggested live demo order

1. Start with **Architecture & method** and explain the five pipeline stages.
2. Use **Chatbot** with Baseline to show a grounded answer and sources.
3. Switch to Corrupted and repeat a factual question to demonstrate the quality risk.
4. Open **Observability** to show the gate failure and stale-data warning.
5. Switch to Repaired and show that the original behavior returns.
