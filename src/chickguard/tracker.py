"""简单质心跟踪器：按最近距离贪心匹配，容忍短时丢失。"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

from .models import Detection, Track


class CentroidTracker:
    def __init__(self, max_distance: float = 80.0, max_lost_seconds: float = 3.0,
                 max_history: int = 5000, max_distance_ratio: Optional[float] = None):
        # max_distance_ratio 不为空时，匹配距离 = ratio * 该轨迹的体长（与画面分辨率无关）
        self.max_distance = max_distance
        self.max_distance_ratio = max_distance_ratio
        self.max_lost_seconds = max_lost_seconds
        self.max_history = max_history
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1

    @property
    def total_tracks(self) -> int:
        """历史上创建过的轨迹总数；远大于画面中的鸡数说明跟踪经常断裂。"""
        return self._next_id - 1

    def update(self, frame_idx: int, detections: List[Detection], fps: float) -> List[Track]:
        pairs = []
        for t in self._tracks.values():
            tx, ty = t.position
            limit = (self.max_distance_ratio * t.diagonal
                     if self.max_distance_ratio else self.max_distance)
            for di, d in enumerate(detections):
                cx, cy = d.center
                dist = math.hypot(cx - tx, cy - ty)
                if dist <= limit:
                    pairs.append((dist, t.track_id, di))
        pairs.sort()

        used_tracks, used_dets = set(), set()
        for _, tid, di in pairs:
            if tid in used_tracks or di in used_dets:
                continue
            self._tracks[tid].add(frame_idx, detections[di], self.max_history)
            used_tracks.add(tid)
            used_dets.add(di)

        for di, d in enumerate(detections):
            if di in used_dets:
                continue
            t = Track(track_id=self._next_id, born=frame_idx, diagonal=d.diagonal)
            t.add(frame_idx, d, self.max_history)
            self._tracks[t.track_id] = t
            self._next_id += 1

        max_lost = self.max_lost_seconds * fps
        for tid in [k for k, t in self._tracks.items() if frame_idx - t.last_seen > max_lost]:
            del self._tracks[tid]
        return list(self._tracks.values())
