# RAG Data Observability UI Demo

This local Gradio app demonstrates the lab in three states:

- **Baseline (clean):** query the clean ChromaDB collection.
- **Corrupted:** inspect how poisoned data degrades retrieval and triggers quality failures.
- **Repaired:** verify that rebuilding from the raw artifact restores the clean state.

It has a sidebar dashboard with five views: a retrieval-grounded chatbot, semantic search, observability dashboard, architecture/method view, and a test-scenario checklist. The chatbot view presents the answer beside ranked evidence cards, so the retrieved documents are visible during a demo. The app reads the generated artifacts under `../data/`; it never displays `.env` values or API keys.

For presentation support, see [Architecture notes](ARCHITECTURE.md), [Test scenarios](TEST_SCENARIOS.md), and [Vietnamese chatbot scenarios](CHAT_SCENARIOS.md).

## Run

From the repository root, after completing Phases 1–6:

```bash
source .venv/bin/activate
python -m pip install -r ui_demo/requirements.txt
python ui_demo/app.py
```

Gradio will print the local URL (normally `http://127.0.0.1:7860`) in your terminal. Open that URL in a browser, then stop the server with `Ctrl+C`.

To use another port, for example `7862`:

```bash
UI_DEMO_PORT=7862 python ui_demo/app.py
```

If a corpus state is unavailable, run:

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```
