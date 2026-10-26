import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

import yaml

from chickguard.config import load_config
from chickguard.detectors import ScriptedDetector
from chickguard.models import Detection
from chickguard.service import analyze
from chickguard.storage import EventStore


def make_video(path, n=60, w=320, h=240, fps=10.0):
    wr = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    for _ in range(n):
        wr.write(np.zeros((h, w, 3), dtype=np.uint8))
    wr.release()


def cfg_short():
    cfg = load_config("config/default.yaml")
    cfg["rules"] = [{"name": "inactivity", "params": {"window_seconds": 2, "move_ratio": 0.3}}]
    cfg["pipeline"].update(stride=1, max_width=160)   # 同时测试缩放
    return cfg


def test_analyze_returns_events_stats_and_video(tmp_path):
    video = str(tmp_path / "in.avi")
    make_video(video)
    det = ScriptedDetector(lambda i: [Detection((20, 20, 40, 40))])  # 缩放后坐标系
    store = EventStore(":memory:")
    progress = []
    r = analyze(video, cfg_short(), out_path=str(tmp_path / "out.mp4"), detector=det,
                store=store, progress=progress.append)

    assert r.source_size == (320, 240) and r.processed_size == (160, 120)
    assert r.frames_processed == 60 and r.total_tracks == 1
    assert len(r.events) == 1 and len(store.list_events()) == 1
    assert r.avg_detections == 1.0 and r.proc_fps > 0
    assert progress and progress[-1] == 1.0
    assert r.video_path and (tmp_path / "out.mp4").exists()
    assert len(r.snapshots) == 1


def test_h264_transcode_when_ffmpeg_available(tmp_path):
    pytest.importorskip("imageio_ffmpeg")
    video = str(tmp_path / "in.avi")
    make_video(video)
    det = ScriptedDetector(lambda i: [])
    r = analyze(video, cfg_short(), out_path=str(tmp_path / "o.mp4"), detector=det)
    assert r.playable and r.video_path.endswith("_h264.mp4")
    cap = cv2.VideoCapture(r.video_path)
    assert cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT) >= 50
    cap.release()


def test_analyze_without_video_output(tmp_path):
    video = str(tmp_path / "in.avi")
    make_video(video, n=20)
    r = analyze(video, cfg_short(), out_path=None, detector=ScriptedDetector(lambda i: []))
    assert r.video_path is None and r.snapshots == []


def test_one_snapshot_per_frame_even_with_multiple_events(tmp_path):
    import numpy as np
    from chickguard.annotator import VideoAnnotator
    from chickguard.models import Event

    ann = VideoAnnotator(str(tmp_path / "s.mp4"), src_fps=10.0)
    frame = np.zeros((60, 80, 3), dtype=np.uint8)
    ann.on_event([Event("huddling", 5, 0.5, (1, 2)), Event("outlier", 5, 0.5, (3,))])
    ann.on_frame(6, frame, [], [])
    ann.close()
    assert len(ann.snapshots) == 1
    assert [e.type for e in ann.snapshots[0][0]] == ["huddling", "outlier"]
