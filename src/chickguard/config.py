"""读取 YAML 配置并构造对象（工厂方法）。"""
from __future__ import annotations

from typing import Optional

import yaml

from .alert_manager import AlertManager
from .detectors.base import Detector
from .pipeline import Pipeline
from .rules import REGISTRY as RULE_REGISTRY
from .storage import EventStore
from .tracker import CentroidTracker


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_detector(cfg: dict) -> Detector:
    name = cfg["detector"]["name"]
    params = cfg["detector"].get("params", {})
    if name == "yolo":
        from .detectors.yolo_detector import YoloDetector  # 延迟导入，避免强依赖
        return YoloDetector(**params)
    raise ValueError(f"未知检测器: {name}")


def build_pipeline(cfg: dict, detector: Optional[Detector] = None,
                   store: Optional[EventStore] = None) -> Pipeline:
    detector = detector or build_detector(cfg)
    rules = []
    for item in cfg.get("rules", []):
        if item["name"] not in RULE_REGISTRY:
            raise ValueError(f"未知规则: {item['name']}")
        rules.append(RULE_REGISTRY[item["name"]](**item.get("params", {})))
    tracker = CentroidTracker(**cfg.get("tracker", {}))
    acfg = cfg.get("alert", {})
    alert = AlertManager(cooldown_seconds=acfg.get("cooldown_seconds", 30.0), store=store,
                         overlap_threshold=acfg.get("overlap_threshold", 0.5))
    interval = cfg.get("pipeline", {}).get("eval_interval_seconds", 1.0)
    return Pipeline(detector, tracker, rules, alert, eval_interval_seconds=interval)
