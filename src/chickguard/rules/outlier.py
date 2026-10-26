"""离群规则：个体距离鸡群中心（取中位数，抗干扰）远超正常范围。"""
from __future__ import annotations

import math
from statistics import median
from typing import List

from ..models import Event, Track
from .base import Rule


class OutlierRule(Rule):
    name = "outlier"

    def __init__(self, outlier_ratio: float = 4.0, min_tracks: int = 5):
        self.outlier_ratio = outlier_ratio
        self.min_tracks = min_tracks

    def evaluate(self, tracks: List[Track], frame_idx: int, fps: float) -> List[Event]:
        live = [t for t in tracks if frame_idx - t.last_seen <= fps]
        if len(live) < self.min_tracks:
            return []
        cx = median(t.position[0] for t in live)
        cy = median(t.position[1] for t in live)
        dists = {t.track_id: math.hypot(t.position[0] - cx, t.position[1] - cy) for t in live}
        mean_diag = sum(t.diagonal for t in live) / len(live)
        limit = self.outlier_ratio * max(median(dists.values()), mean_diag)
        events = []
        for t in live:
            d = dists[t.track_id]
            if d >= limit:
                events.append(Event(
                    type=self.name, frame_idx=frame_idx, timestamp=frame_idx / fps,
                    track_ids=(t.track_id,), severity=d / limit,
                    message=f"鸡 #{t.track_id} 距鸡群中心 {d:.0f}px，明显离群",
                ))
        return events
