"""视频接入：统一成 (frame_idx, frame) 迭代器，并提供 fps 属性。"""
from __future__ import annotations

from typing import Iterator, List, Optional, Tuple


class FrameSequence:
    """内存中的帧序列，主要用于测试和合成数据。"""

    def __init__(self, frames: List, fps: float = 10.0):
        self._frames = frames
        self.fps = fps

    def __iter__(self) -> Iterator[Tuple[int, object]]:
        return iter(enumerate(self._frames))


class OpenCVVideoSource:
    """读取视频文件；stride=N 表示每 N 帧取 1 帧。"""

    def __init__(self, path: str, stride: int = 1, max_width: Optional[int] = None):
        try:
            import cv2
        except ImportError as e:  # pragma: no cover
            raise ImportError("读取视频需要先安装 opencv-python") from e
        self._cv2 = cv2
        self._path = path
        self.stride = max(1, stride)
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            raise FileNotFoundError(f"无法打开视频: {path}")
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        self.frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        self.source_size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        self.max_width = max_width  # 宽度超过它时先缩小再处理（规则按体长比例，不受影响）
        cap.release()

    def __iter__(self) -> Iterator[Tuple[int, object]]:
        cap = self._cv2.VideoCapture(self._path)
        idx = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if idx % self.stride == 0:
                    h, w = frame.shape[:2]
                    if self.max_width and w > self.max_width:
                        scale = self.max_width / w
                        frame = self._cv2.resize(frame, (self.max_width, int(h * scale)),
                                                 interpolation=self._cv2.INTER_AREA)
                    yield idx, frame
                idx += 1
        finally:
            cap.release()
