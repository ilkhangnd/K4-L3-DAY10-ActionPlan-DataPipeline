from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="RAG pipeline review",
    page_icon=":material/monitoring:",
    layout="wide",
)

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
METRIC_KEYS = (
    "retrieval_hit_rate",
    "mean_token_f1",
    "judge_accuracy",
    "mean_judge_score",
)
STATE_FILES = {
    "Baseline": DATA_DIR / "clean" / "papers_clean.json",
    "Corrupted": DATA_DIR / "clean" / "papers_clean_corrupted.json",
    "Repaired": DATA_DIR / "clean" / "papers_clean_repaired.json",
}
METRIC_FILES = {
    "Baseline": DATA_DIR / "results" / "baseline_metrics.json",
    "Corrupted": DATA_DIR / "results" / "corrupted_metrics.json",
    "Repaired": DATA_DIR / "results" / "repaired_metrics.json",
}
QUALITY_FILES = {
    "Baseline": DATA_DIR / "quality" / "baseline_quality_report.json",
    "Corrupted": DATA_DIR / "quality" / "corrupted_quality_report.json",
    "Repaired": DATA_DIR / "quality" / "repaired_quality_report.json",
}
FRESHNESS_FILES = {
    "Baseline": DATA_DIR / "quality" / "freshness_report.json",
    "Corrupted": DATA_DIR / "quality" / "corrupted_freshness_report.json",
    "Repaired": DATA_DIR / "quality" / "repaired_freshness_report.json",
}


@st.cache_data(ttl="30s", max_entries=32)
def load_json(path_text: str) -> Any:
    return json.loads(Path(path_text).read_text(encoding="utf-8"))


@st.cache_data(ttl="30s", max_entries=8)
def load_dataframe(path_text: str) -> pd.DataFrame:
    return pd.read_json(path_text)


def artifact_status() -> pd.DataFrame:
    artifacts = {
        "Raw records": DATA_DIR / "raw" / "crossref_records.json",
        "Clean dataset": DATA_DIR / "clean" / "papers_clean.json",
        "Evaluation set": DATA_DIR / "eval" / "test_set.json",
        "Baseline metrics": METRIC_FILES["Baseline"],
        "Corruption log": DATA_DIR / "results" / "corruption_log.json",
        "Corrupted metrics": METRIC_FILES["Corrupted"],
        "Repaired metrics": METRIC_FILES["Repaired"],
        "Repair evidence": DATA_DIR / "results" / "repair_verification.json",
        "Comparison report": DATA_DIR / "reports" / "corruption_report.md",
    }
    return pd.DataFrame(
        [
            {
                "artifact": name,
                "status": "Ready" if path.is_file() and path.stat().st_size else "Missing",
                "path": path.relative_to(PROJECT_DIR).as_posix(),
            }
            for name, path in artifacts.items()
        ]
    )


def metric_frame(metrics_by_state: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for state, metrics in metrics_by_state.items():
        for metric in METRIC_KEYS:
            value = float(metrics[metric])
            rows.append(
                {
                    "state": state,
                    "metric": metric,
                    "value": value,
                    "normalized_value": value / 5 if metric == "mean_judge_score" else value,
                }
            )
    return pd.DataFrame(rows)


def quality_frame(
    quality_by_state: dict[str, dict[str, Any]],
    freshness_by_state: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "state": state,
                "GX gate": "PASS" if quality_by_state[state].get("gx_success") else "FAIL",
                "freshness": "FRESH" if freshness_by_state[state].get("is_fresh") else "STALE",
                "stale ratio": float(freshness_by_state[state].get("stale_ratio", 0)),
                "rows": int(freshness_by_state[state].get("total_rows", 0)),
            }
            for state in STATE_FILES
        ]
    )


required_paths = [*METRIC_FILES.values(), *QUALITY_FILES.values(), *FRESHNESS_FILES.values()]
missing_paths = [path for path in required_paths if not path.is_file()]

with st.container(
    horizontal=True,
    horizontal_alignment="distribute",
    vertical_alignment="center",
):
    st.title("RAG pipeline review", icon=":material/monitoring:")
    if st.button("Refresh artifacts", icon=":material/refresh:", type="tertiary"):
        st.cache_data.clear()
        st.rerun()

st.caption("CP5/CP6 evidence dashboard · Crossref → quality gate → ChromaDB → evaluation → repair")

if missing_paths:
    st.error(
        "Run the baseline and corruption pipelines first. Missing: "
        + ", ".join(path.relative_to(PROJECT_DIR).as_posix() for path in missing_paths),
        icon=":material/error:",
    )
    st.stop()

metrics_by_state = {state: load_json(str(path)) for state, path in METRIC_FILES.items()}
quality_by_state = {state: load_json(str(path)) for state, path in QUALITY_FILES.items()}
freshness_by_state = {state: load_json(str(path)) for state, path in FRESHNESS_FILES.items()}
repair = load_json(str(DATA_DIR / "results" / "repair_verification.json"))
corruption_log = load_json(str(DATA_DIR / "results" / "corruption_log.json"))
artifacts = artifact_status()
ready_count = int((artifacts["status"] == "Ready").sum())

with st.container(horizontal=True):
    st.metric("Submission artifacts", f"{ready_count}/{len(artifacts)}", border=True)
    st.metric("Baseline rows", freshness_by_state["Baseline"]["total_rows"], border=True)
    st.metric(
        "Corrupted gate",
        "Detected" if not quality_by_state["Corrupted"]["success"] else "Not detected",
        border=True,
    )
    st.metric("Repair idempotent", "Yes" if repair.get("idempotent") else "No", border=True)

overview_tab, metrics_tab, quality_tab, data_tab, evidence_tab = st.tabs(
    [
        ":material/dashboard: Overview",
        ":material/query_stats: Metrics",
        ":material/verified: Quality",
        ":material/table_chart: Data explorer",
        ":material/folder_open: Evidence",
    ]
)

with overview_tab:
    st.header("Pipeline health", icon=":material/health_and_safety:")
    if ready_count == len(artifacts) and repair.get("baseline_matches_repaired"):
        st.success(
            "Automated CP6 evidence is complete: corruption was detected and repair restored the baseline.",
            icon=":material/check_circle:",
        )
    else:
        st.warning("Some submission evidence still needs attention.", icon=":material/warning:")

    comparison = metric_frame(metrics_by_state)
    chart = (
        alt.Chart(comparison)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("state:N", title=None, sort=["Baseline", "Corrupted", "Repaired"]),
            xOffset=alt.XOffset("metric:N"),
            y=alt.Y("normalized_value:Q", title="Normalized score", scale=alt.Scale(domain=[0, 1])),
            color=alt.Color("metric:N", title="Metric"),
            tooltip=[
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Value", format=".4f"),
            ],
        )
        .properties(height=340)
    )
    with st.container(border=True):
        st.subheader("Baseline → corrupted → repaired")
        st.altair_chart(chart, width="stretch")

    st.subheader("Artifact readiness", icon=":material/checklist:")
    st.dataframe(artifacts, hide_index=True, width="stretch")

with metrics_tab:
    st.header("Evaluation metrics", icon=":material/query_stats:")
    selected_metric = st.segmented_control(
        "Metric",
        options=list(METRIC_KEYS),
        default="retrieval_hit_rate",
        key="selected_metric",
        required=True,
        width="stretch",
    )
    selected_values = {
        state: float(metrics[selected_metric]) for state, metrics in metrics_by_state.items()
    }
    with st.container(horizontal=True):
        st.metric("Baseline", f"{selected_values['Baseline']:.4f}", border=True)
        st.metric(
            "Corrupted",
            f"{selected_values['Corrupted']:.4f}",
            delta=f"{selected_values['Corrupted'] - selected_values['Baseline']:+.4f}",
            border=True,
        )
        st.metric(
            "Repaired",
            f"{selected_values['Repaired']:.4f}",
            delta=f"{selected_values['Repaired'] - selected_values['Corrupted']:+.4f}",
            border=True,
        )

    wide_metrics = comparison.pivot(index="metric", columns="state", values="value").reset_index()
    wide_metrics["corruption delta"] = wide_metrics["Corrupted"] - wide_metrics["Baseline"]
    wide_metrics["recovery delta"] = wide_metrics["Repaired"] - wide_metrics["Corrupted"]
    st.dataframe(wide_metrics.round(4), hide_index=True, width="stretch")

with quality_tab:
    st.header("Quality and freshness", icon=":material/verified:")
    quality_summary = quality_frame(quality_by_state, freshness_by_state)
    st.dataframe(
        quality_summary,
        hide_index=True,
        width="stretch",
        column_config={
            "stale ratio": st.column_config.ProgressColumn(
                "Stale ratio", min_value=0.0, max_value=1.0, format="percent"
            ),
        },
    )

    st.subheader("Six controlled corruption scenarios", icon=":material/bug_report:")
    scenarios = pd.DataFrame(corruption_log["scenarios"])
    scenarios["parameters"] = scenarios["parameters"].map(
        lambda value: json.dumps(value, ensure_ascii=False)
    )
    st.dataframe(
        scenarios[["corruption_type", "affected_count", "paper_ids", "parameters"]],
        hide_index=True,
        width="stretch",
    )

    with st.expander("Idempotency proof", icon=":material/fingerprint:"):
        st.json(repair, expanded=True)

with data_tab:
    st.header("Dataset explorer", icon=":material/table_chart:")
    state = st.segmented_control(
        "Dataset state",
        options=list(STATE_FILES),
        default="Baseline",
        key="dataset_state",
        required=True,
    )
    query = st.text_input("Filter by paper ID or title", placeholder="Type a DOI or title keyword")
    dataset = load_dataframe(str(STATE_FILES[state]))
    if query:
        mask = (
            dataset["paper_id"].astype(str).str.contains(query, case=False, na=False, regex=False)
            | dataset["title"].astype(str).str.contains(query, case=False, na=False, regex=False)
        )
        dataset = dataset.loc[mask]
    visible_columns = [
        column for column in ("paper_id", "title", "published", "age_days", "summary_chars")
        if column in dataset.columns
    ]
    st.caption(f"Showing {len(dataset)} records from {state.lower()} data.")
    st.dataframe(dataset[visible_columns], hide_index=True, width="stretch", height=440)

with evidence_tab:
    st.header("Reports and submission evidence", icon=":material/folder_open:")
    report_choice = st.segmented_control(
        "Report",
        options=["Phase 1", "Corruption & repair", "Trần Long Khánh"],
        default="Corruption & repair",
        key="report_choice",
        required=True,
    )
    report_paths = {
        "Phase 1": DATA_DIR / "reports" / "phase1_report.md",
        "Corruption & repair": DATA_DIR / "reports" / "corruption_report.md",
        "Trần Long Khánh": PROJECT_DIR / "report" / "TranLongKhanh.md",
    }
    report_path = report_paths[report_choice]
    if report_path.is_file():
        st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.warning(f"Missing report: {report_path.relative_to(PROJECT_DIR)}")

    st.info(
        "Manual CP6 steps remain: confirm TEAM.md identities, verify every member in GitHub Insights → "
        "Contributors, and submit the repository link on LMS.",
        icon=":material/info:",
    )
