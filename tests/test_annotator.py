import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from chickguard.annotator import VideoAnnotator
from chickguard.config import build_pipeline
from chickguard.detectors import ScriptedDetector
from chickguard.models import Detection
from chickguard.video_source import FrameSequence
import yaml


def test_annotated_video_is_written_with_events(tmp_path):
    with open("config/default.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg["rules"] = [{"name": "inactivity", "params": {"window_seconds": 2, "move_ratio": 0.3}}]

    det = ScriptedDetector(lambda i: [Detection((50, 50, 90, 90))])  # 一只静止的鸡
    frames = [np.zeros((120, 160, 3), dtype=np.uint8) for _ in range(60)]
    out = str(tmp_path / "out.mp4")
    ann = VideoAnnotator(out, src_fps=10.0, stride=1)
    pipe = build_pipeline(cfg, detector=det)
    pipe.on_frame, pipe.on_event = ann.on_frame, ann.on_event
    result = pipe.run(FrameSequence(frames, fps=10.0))
    ann.close()

    assert len(result.events) == 1
    cap = cv2.VideoCapture(out)
    assert cap.isOpened() and int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) >= 50
    cap.release()
