from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys

from core.config import load_settings
from core.utils import read_json
from ingestion.corruption import CORRUPTION_SCENARIOS


def main() -> None:
    """Validate CP0-CP6 artifacts without calling a network service."""
    settings = load_settings()
    paths = settings.paths
    checks: list[tuple[str, Callable[[], bool]]] = [
        ("raw Crossref response", lambda: _nonempty(paths.raw_api_response)),
        ("normalized raw records", lambda: _nonempty(paths.raw_records_json)),
        ("clean CSV and JSON", lambda: _nonempty(paths.clean_csv) and _nonempty(paths.clean_json)),
        ("fixed 10-question test set", lambda: _valid_test_set(paths.eval_testset)),
        ("baseline metrics", lambda: _valid_metrics(paths.baseline_metrics)),
        ("six corruption scenarios", lambda: _valid_corruption_log(paths.corruption_log)),
        ("corrupted metrics", lambda: _valid_metrics(paths.corrupted_metrics)),
        ("repaired metrics", lambda: _valid_metrics(paths.repaired_metrics)),
        ("idempotent repair evidence", lambda: _valid_repair(paths.repair_verification)),
        ("quality state transition", lambda: _valid_quality_transition(paths)),
        ("three-state report", lambda: _valid_report(paths.comparison_report)),
        ("Streamlit review dashboard", lambda: _nonempty(paths.project_dir / "streamlit_app.py")),
        ("measurable degradation and recovery", lambda: _valid_metric_transition(paths)),
    ]

    failures = []
    print("CP6 submission verification")
    print("=" * 52)
    for label, check in checks:
        try:
            passed = bool(check())
        except Exception as exc:
            passed = False
            failures.append(f"{label}: {exc}")
        else:
            if not passed:
                failures.append(label)
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")

    if failures:
        print("\nSubmission is not ready:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nAll automated CP6 checks passed.")
    print("Manual checks still required: TEAM.md identities, GitHub contributors, and LMS submission.")


def _nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _valid_test_set(path: Path) -> bool:
    data = read_json(path)
    return (
        isinstance(data, list)
        and len(data) == 10
        and {item.get("question_type") for item in data} == {"summary", "authors", "date", "categories"}
    )


def _valid_metrics(path: Path) -> bool:
    data = read_json(path)
    required = {"samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"}
    return required.issubset(data) and data["samples"] == 10


def _valid_corruption_log(path: Path) -> bool:
    data = read_json(path)
    names = tuple(item.get("corruption_type") for item in data.get("scenarios", []))
    return data.get("scenario_count") == 6 and names == CORRUPTION_SCENARIOS


def _valid_repair(path: Path) -> bool:
    data = read_json(path)
    return all(
        data.get(key) is True
        for key in ("repair_triggered_by_failed_gate", "idempotent", "baseline_matches_repaired", "test_set_unchanged")
    )


def _valid_quality_transition(paths) -> bool:
    baseline = read_json(paths.baseline_quality_report)
    corrupted = read_json(paths.corrupted_quality_report)
    repaired = read_json(paths.repaired_quality_report)
    return baseline.get("success") is True and corrupted.get("success") is False and repaired.get("success") is True


def _valid_report(path: Path) -> bool:
    if not _nonempty(path):
        return False
    text = path.read_text(encoding="utf-8")
    return all(state in text for state in ("Baseline", "Corrupted", "Repaired"))


def _valid_metric_transition(paths) -> bool:
    baseline = read_json(paths.baseline_metrics)
    corrupted = read_json(paths.corrupted_metrics)
    repaired = read_json(paths.repaired_metrics)
    keys = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    degraded = any(corrupted[key] < baseline[key] for key in keys)
    recovered = all(repaired[key] >= baseline[key] - 1e-9 for key in keys)
    return degraded and recovered


if __name__ == "__main__":
    main()
