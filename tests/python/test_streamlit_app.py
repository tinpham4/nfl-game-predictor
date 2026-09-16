from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_dashboard_starts_and_handles_team_selection():
    app_path = Path(__file__).parents[2] / "app.py"
    app = AppTest.from_file(app_path, default_timeout=20).run()

    assert not app.exception
    assert len(app.metric) >= 8
    assert app.sidebar.selectbox[0].value == "MIN"

    app.sidebar.selectbox[0].select("BUF").run()

    assert not app.exception
    assert app.sidebar.selectbox[0].value == "BUF"
