"""核心数据结构：Detection / Track / Event。"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Tuple

BBox = Tuple[float, float, float, float]  # x1, y1, x2, y2


@dataclass(frozen=True)
class Detection:
    """单帧中的一个检测结果。"""
    bbox: BBox
    confidence: float = 1.0
    label: str = "chicken"

    @property
    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def diagonal(self) -> float:
        x1, y1, x2, y2 = self.bbox
        return math.hypot(x2 - x1, y2 - y1)


@dataclass
class Track:
    """跨帧关联后的一只鸡的轨迹。history 中每项为 (frame_idx, cx, cy)。"""
    track_id: int
    born: int                      # 轨迹创建时的帧号
    diagonal: float                # 平滑后的检测框对角线长度（作为尺度参照）
    history: List[Tuple[int, float, float]] = field(default_factory=list)

    @property
    def last_seen(self) -> int:
        return self.history[-1][0] if self.history else self.born

    @property
    def position(self) -> Tuple[float, float]:
        _, x, y = self.history[-1]
        return (x, y)

    def add(self, frame_idx: int, det: Detection, max_history: int) -> None:
        cx, cy = det.center
        self.history.append((frame_idx, cx, cy))
        if len(self.history) > max_history:
            del self.history[: len(self.history) - max_history]
        self.diagonal = 0.9 * self.diagonal + 0.1 * det.diagonal


@dataclass(frozen=True)
class Event:
    """规则判定出的异常事件。"""
    type: str                      # inactivity / huddling / outlier
    frame_idx: int
    timestamp: float               # 秒
    track_ids: Tuple[int, ...]
    severity: float = 1.0
    message: str = ""
