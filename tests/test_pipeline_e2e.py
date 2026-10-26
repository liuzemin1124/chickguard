"""端到端 / 接口契约测试：用脚本化的假检测器代替 YOLO，证明检测器可替换。"""
import math

import yaml

from chickguard.config import build_pipeline
from chickguard.detectors import Detector, ScriptedDetector
from chickguard.models import Detection
from chickguard.storage import EventStore
from chickguard.video_source import FrameSequence

FPS = 10.0
N_FRAMES = 300  # 30 秒


def scene(frame_idx):
    """10 只鸡排成 2x5 网格；第 0 号一动不动，其余做正弦摆动。"""
    dets = []
    for i in range(10):
        bx, by = (i % 5) * 200 + 100, (i // 5) * 200 + 100
        dx = 0.0 if i == 0 else 60 * math.sin(2 * math.pi * frame_idx / 40 + i)
        x, y = bx + dx, by
        dets.append(Detection((x - 20, y - 20, x + 20, y + 20)))
    return dets


def load_cfg():
    with open("config/default.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_pipeline_flags_only_the_static_chicken():
    pipe = build_pipeline(load_cfg(), detector=ScriptedDetector(scene))
    result = pipe.run(FrameSequence(list(range(N_FRAMES)), fps=FPS))
    assert result.frames_processed == N_FRAMES
    assert {e.type for e in result.events} == {"inactivity"}
    assert len(result.events) == 1             # 冷却去重后只报一次
    assert len(result.events[0].track_ids) == 1


def test_any_detector_implementation_can_be_plugged_in():
    class AlwaysEmpty(Detector):
        def detect(self, frame):
            return []

    pipe = build_pipeline(load_cfg(), detector=AlwaysEmpty())
    result = pipe.run(FrameSequence(list(range(50)), fps=FPS))
    assert result.events == [] and result.frames_processed == 50


def test_events_are_persisted_by_pipeline():
    store = EventStore(":memory:")
    pipe = build_pipeline(load_cfg(), detector=ScriptedDetector(scene), store=store)
    pipe.run(FrameSequence(list(range(N_FRAMES)), fps=FPS))
    assert len(store.list_events("inactivity")) == 1
