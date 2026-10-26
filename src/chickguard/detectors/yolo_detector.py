"""默认检测器：封装 Ultralytics YOLO。ultralytics 仅在实例化时才导入。"""
from __future__ import annotations

from typing import Iterable, List, Optional

from ..models import Detection
from .base import Detector


class YoloDetector(Detector):
    def __init__(self, model_path: str = "yolov8n.pt", confidence: float = 0.3,
                 classes: Optional[Iterable[str]] = ("bird",)):
        try:
            from ultralytics import YOLO
        except ImportError as e:  # pragma: no cover
            raise ImportError("使用 YoloDetector 需要先安装 ultralytics") from e
        self._model = YOLO(model_path)
        self._confidence = confidence
        # COCO 预训练模型没有 chicken 类，鸡通常被识别为 bird；自训练模型可改类名
        self._classes = set(classes) if classes else None

    def detect(self, frame) -> List[Detection]:
        result = self._model.predict(frame, conf=self._confidence, verbose=False)[0]
        detections = []
        for box in result.boxes:
            name = result.names[int(box.cls)]
            if self._classes and name not in self._classes:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            detections.append(Detection((x1, y1, x2, y2), float(box.conf), name))
        return detections
