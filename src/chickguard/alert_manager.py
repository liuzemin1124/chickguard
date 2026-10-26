"""告警管理：把「同一件事」的重复告警合并，并落库。

判定为同一件事：类型相同、仍在冷却期内、且涉及的目标有足够的重叠。
- 单目标事件（不活动、离群）：目标相同即重叠
- 群体事件（扎堆）：鸡群成员每秒都在小幅变化，不能要求编号集合完全相同，
  所以用重叠系数 |A∩B| / min(|A|,|B|) 与阈值比较
"""
from __future__ import annotations

from typing import FrozenSet, List, Optional, Tuple

from .models import Event
from .storage import EventStore


class AlertManager:
    def __init__(self, cooldown_seconds: float = 30.0, store: Optional[EventStore] = None,
                 overlap_threshold: float = 0.5):
        self.cooldown_seconds = cooldown_seconds
        self.overlap_threshold = overlap_threshold
        self._store = store
        self._recent: List[Tuple[str, FrozenSet[int], float]] = []  # 已发出的告警

    def _is_duplicate(self, e: Event) -> bool:
        ids = frozenset(e.track_ids)
        if not ids:
            return False
        for kind, prev, ts in self._recent:
            if kind != e.type or e.timestamp - ts >= self.cooldown_seconds:
                continue
            overlap = len(ids & prev) / min(len(ids), len(prev))
            if overlap >= self.overlap_threshold:
                return True
        return False

    def submit(self, events: List[Event]) -> List[Event]:
        accepted = []
        for e in events:
            if self._is_duplicate(e):
                continue
            accepted.append(e)
            self._recent.append((e.type, frozenset(e.track_ids), e.timestamp))
            if self._store is not None:
                self._store.save(e)
        if events:  # 清理已过冷却期的记录
            now = max(e.timestamp for e in events)
            self._recent = [r for r in self._recent if now - r[2] < self.cooldown_seconds]
        return accepted
