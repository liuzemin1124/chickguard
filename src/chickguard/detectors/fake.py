"""假检测器：按脚本返回检测结果，用于测试与证明检测器可替换。"""
from __future__ import annotations

from typing import Callable, List

from ..models import Detection
from .base import Detector


class ScriptedDetector(Detector):
    """frame 在这里就是帧号，script(frame_idx) -> List[Detection]。"""

    def __init__(self, script: Callable[[int], List[Detection]]):
        self._script = script

    def detect(self, frame) -> List[Detection]:
        return self._script(frame)
