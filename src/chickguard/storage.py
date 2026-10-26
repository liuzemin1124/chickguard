"""SQLite 事件存储，隔离数据库细节。"""
from __future__ import annotations

import sqlite3
from typing import List, Optional

from .models import Event


class EventStore:
    def __init__(self, path: str = ":memory:"):
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, frame_idx INTEGER NOT NULL, timestamp REAL NOT NULL,
                track_ids TEXT NOT NULL, severity REAL NOT NULL, message TEXT NOT NULL)"""
        )
        self._conn.commit()

    def save(self, event: Event) -> None:
        self._conn.execute(
            "INSERT INTO events (type, frame_idx, timestamp, track_ids, severity, message) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (event.type, event.frame_idx, event.timestamp,
             ",".join(map(str, event.track_ids)), event.severity, event.message),
        )
        self._conn.commit()

    def list_events(self, event_type: Optional[str] = None) -> List[Event]:
        sql = "SELECT type, frame_idx, timestamp, track_ids, severity, message FROM events"
        args: tuple = ()
        if event_type:
            sql += " WHERE type = ?"
            args = (event_type,)
        rows = self._conn.execute(sql + " ORDER BY timestamp, id", args).fetchall()
        return [Event(r[0], r[1], r[2], tuple(int(x) for x in r[3].split(",") if x), r[4], r[5])
                for r in rows]

    def clear(self) -> None:
        self._conn.execute("DELETE FROM events")
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
