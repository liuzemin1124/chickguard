"""不活动规则：一只鸡在一段时间内几乎没有位移。"""
from __future__ import annotations

import math
from typing import List

from ..models import Event, Track
from .base import Rule


class InactivityRule(Rule):
    name = "inactivity"

    def __init__(self, window_seconds: float = 10.0, move_ratio: float = 0.3):
        self.window_seconds = window_seconds
        self.move_ratio = move_ratio  # 位移阈值 = move_ratio * 体长(检测框对角线)

    def evaluate(self, tracks: List[Track], frame_idx: int, fps: float) -> List[Event]:
        window = self.window_seconds * fps
        tol = max(1.0, 0.1 * window)  # 窗口两端允许的采样缺口
        events = []
        for t in tracks:
            if frame_idx - t.born < window:
                continue
            pts = [(f, x, y) for f, x, y in t.history if f >= frame_idx - window]
            if len(pts) < 2:
                continue
            if pts[0][0] > frame_idx - window + tol or pts[-1][0] < frame_idx - tol:
                continue  # 窗口没有被轨迹充分覆盖（中途丢失等）
            xs = [p[1] for p in pts]
            ys = [p[2] for p in pts]
            displacement = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
            limit = self.move_ratio * t.diagonal
            if displacement < limit:
                events.append(Event(
                    type=self.name, frame_idx=frame_idx, timestamp=frame_idx / fps,
                    track_ids=(t.track_id,),
                    severity=1.0 - displacement / limit if limit > 0 else 1.0,
                    message=f"鸡 #{t.track_id} 在 {self.window_seconds:.0f}s 内位移仅 {displacement:.1f}px",
                ))
        return events
