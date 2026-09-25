from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_dashboard_renders_verified_artifacts() -> None:
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=15).run()

    assert not app.exception
    assert app.title[0].value == "RAG pipeline review"
    assert len(app.metric) >= 4
    assert app.metric[0].value == "9/9"
    assert app.success


def test_dashboard_switches_metric() -> None:
    app_path = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    app = AppTest.from_file(str(app_path), default_timeout=15).run()

    app.segmented_control(key="selected_metric").select("mean_token_f1").run()

    assert not app.exception
    assert app.segmented_control(key="selected_metric").value == "mean_token_f1"
