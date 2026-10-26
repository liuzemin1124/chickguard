"""规则接口（策略模式）：每条规则一个类，新增规则不需要修改 Pipeline。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import Event, Track


class Rule(ABC):
    name = "rule"

    @abstractmethod
    def evaluate(self, tracks: List[Track], frame_idx: int, fps: float) -> List[Event]:
        """根据当前所有轨迹判定异常，返回事件列表。"""
