"""流水线控制器：视频 -> 检测 -> 跟踪 -> 规则 -> 告警。依赖注入，不依赖具体实现。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .alert_manager import AlertManager
from .detectors.base import Detector
from .models import Event, Track
from .rules.base import Rule
from .tracker import CentroidTracker


@dataclass
class PipelineResult:
    events: List[Event] = field(default_factory=list)
    frames_processed: int = 0
    duration_seconds: float = 0.0


class Pipeline:
    def __init__(self, detector: Detector, tracker: CentroidTracker, rules: List[Rule],
                 alert_manager: AlertManager, eval_interval_seconds: float = 1.0,
                 on_frame: Optional[Callable] = None,
                 on_event: Optional[Callable] = None):
        self.detector = detector
        self.tracker = tracker
        self.rules = rules
        self.alert_manager = alert_manager
        self.eval_interval_seconds = eval_interval_seconds
        self.on_frame = on_frame  # 可选钩子：(frame_idx, frame, detections, tracks) -> None
        self.on_event = on_event  # 可选钩子：(accepted_events) -> None

    def run(self, source) -> PipelineResult:
        fps = float(source.fps)
        result = PipelineResult()
        last_eval = None
        last_idx = 0
        for frame_idx, frame in source:
            detections = self.detector.detect(frame)
            tracks: List[Track] = self.tracker.update(frame_idx, detections, fps)
            if self.on_frame:
                self.on_frame(frame_idx, frame, detections, tracks)
            if last_eval is None or frame_idx - last_eval >= self.eval_interval_seconds * fps:
                last_eval = frame_idx
                for rule in self.rules:
                    accepted = self.alert_manager.submit(rule.evaluate(tracks, frame_idx, fps))
                    result.events.extend(accepted)
                    if accepted and self.on_event:
                        self.on_event(accepted)
            result.frames_processed += 1
            last_idx = frame_idx
        result.duration_seconds = last_idx / fps if fps else 0.0
        return result
