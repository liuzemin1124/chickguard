from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "src" / "chickguard" / "app.py")


def test_app_renders_without_exception():
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    assert any("ChickGuard" in t.value for t in at.title)


def test_app_renders_a_result_with_many_snapshots():
    np = pytest.importorskip("numpy")
    from chickguard.models import Event
    from chickguard.service import AnalysisResult

    events = [Event("huddling", 10, 1.0, (1, 2, 3)), Event("inactivity", 20, 2.0, (4,))]
    shots = [([events[i % 2]], np.zeros((60, 80, 3), dtype=np.uint8)) for i in range(14)]
    fake = AnalysisResult(
        events=events, frames_processed=100, duration_seconds=10.0, elapsed_seconds=5.0,
        source_size=(3840, 2160), processed_size=(1280, 720), video_fps=30.0, stride=2,
        avg_detections=9.0, avg_diagonal=120.0, total_tracks=20, snapshots=shots)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["result"] = fake
    at.run()
    assert not at.exception
