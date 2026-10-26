"""扎堆规则：局部区域内聚集的个体数量超过阈值。"""
from __future__ import annotations

import math
from typing import List

from ..models import Event, Track
from .base import Rule


class HuddlingRule(Rule):
    name = "huddling"

    def __init__(self, radius_ratio: float = 1.5, min_members: int = 6):
        self.radius_ratio = radius_ratio  # 邻域半径 = radius_ratio * 平均体长
        self.min_members = min_members

    def evaluate(self, tracks: List[Track], frame_idx: int, fps: float) -> List[Event]:
        # 只看当前帧附近仍在场的轨迹
        live = [t for t in tracks if frame_idx - t.last_seen <= fps]
        if len(live) < self.min_members:
            return []
        radius = self.radius_ratio * (sum(t.diagonal for t in live) / len(live))
        remaining = list(live)
        events = []
        while remaining:
            seed = remaining[0]
            sx, sy = seed.position
            group = [t for t in remaining
                     if math.hypot(t.position[0] - sx, t.position[1] - sy) <= radius]
            if len(group) >= self.min_members:
                events.append(Event(
                    type=self.name, frame_idx=frame_idx, timestamp=frame_idx / fps,
                    track_ids=tuple(sorted(t.track_id for t in group)),
                    severity=len(group) / self.min_members,
                    message=f"{len(group)} 只鸡聚集在半径 {radius:.0f}px 内",
                ))
                ids = {t.track_id for t in group}
                remaining = [t for t in remaining if t.track_id not in ids]
            else:
                remaining.pop(0)
        return events
