"""检测器接口（策略模式）：任何模型只要实现 detect() 即可接入。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from ..models import Detection


class Detector(ABC):
    @abstractmethod
    def detect(self, frame) -> List[Detection]:
        """输入一帧图像（numpy 数组或任意对象），返回检测结果列表。"""
