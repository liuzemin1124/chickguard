"""应用服务：把「读视频 → 跑流水线 → 出标注视频 → 汇总统计」封装成一个函数，
命令行和 Streamlit 界面共用，界面层不含业务逻辑。"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from .annotator import VideoAnnotator, to_browser_mp4
from .config import build_pipeline
from .detectors.base import Detector
from .models import Event
from .storage import EventStore
from .video_source import OpenCVVideoSource


@dataclass
class AnalysisResult:
    events: List[Event]
    frames_processed: int
    duration_seconds: float
    elapsed_seconds: float
    source_size: Tuple[int, int]
    processed_size: Optional[Tuple[int, int]]
    video_fps: float
    stride: int
    avg_detections: float
    avg_diagonal: float
    total_tracks: int
    video_path: Optional[str] = None     # 标注视频（优先返回浏览器可播放的 H.264 版本）
    playable: bool = False
    snapshots: list = field(default_factory=list)

    @property
    def proc_fps(self) -> float:
        return self.frames_processed / self.elapsed_seconds if self.elapsed_seconds else 0.0


class _Stats:
    def __init__(self):
        self.frames = 0
        self.dets = 0
        self.diag_sum = 0.0
        self.size: Optional[Tuple[int, int]] = None

    def on_frame(self, frame_idx, frame, detections, tracks):
        if self.size is None:
            h, w = frame.shape[:2]
            self.size = (w, h)
        self.frames += 1
        self.dets += len(detections)
        self.diag_sum += sum(d.diagonal for d in detections)


def analyze(video_path: str, cfg: dict, out_path: Optional[str] = None,
            detector: Optional[Detector] = None, store: Optional[EventStore] = None,
            progress: Optional[Callable[[float], None]] = None) -> AnalysisResult:
    pcfg = cfg.get("pipeline", {})
    stride = pcfg.get("stride", 1)
    source = OpenCVVideoSource(video_path, stride=stride, max_width=pcfg.get("max_width"))
    pipeline = build_pipeline(cfg, detector=detector, store=store)

    stats = _Stats()
    annotator = None
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        annotator = VideoAnnotator(out_path, src_fps=source.fps, stride=stride, max_width=10 ** 6)
        pipeline.on_event = annotator.on_event

    total = source.frame_count

    def on_frame(idx, frame, dets, tracks):
        stats.on_frame(idx, frame, dets, tracks)
        if annotator:
            annotator.on_frame(idx, frame, dets, tracks)
        if progress and total:
            progress(min(1.0, idx / total))

    pipeline.on_frame = on_frame
    t0 = time.perf_counter()
    try:
        result = pipeline.run(source)
    finally:
        if annotator:
            annotator.close()
    elapsed = time.perf_counter() - t0
    if progress:
        progress(1.0)

    video_path_out, playable = None, False
    if annotator:
        h264 = os.path.splitext(out_path)[0] + "_h264.mp4"
        playable = to_browser_mp4(out_path, h264)
        video_path_out = h264 if playable else out_path

    return AnalysisResult(
        events=result.events, frames_processed=result.frames_processed,
        duration_seconds=result.duration_seconds, elapsed_seconds=elapsed,
        source_size=source.source_size, processed_size=stats.size,
        video_fps=source.fps, stride=stride,
        avg_detections=stats.dets / stats.frames if stats.frames else 0.0,
        avg_diagonal=stats.diag_sum / stats.dets if stats.dets else 0.0,
        total_tracks=pipeline.tracker.total_tracks,
        video_path=video_path_out, playable=playable,
        snapshots=annotator.snapshots if annotator else [])
