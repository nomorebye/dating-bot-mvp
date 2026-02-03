from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DEFAULT_DB_PATH = os.getenv("MEMORY_DB_PATH", "memory.db")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)


def default_state() -> Dict[str, Any]:
    return {
        "persona_id": "noona",
        "rel_stage": "some",
        "rel_score": 40,
        "trust": 40,
        "boundaries_level": 0,
        "last_user_message_at": None,
        "last_bot_message_at": None,
        "realtime_until": None,
        "last_meal_time": None,
        "last_meal_desc": None,
        "last_asked_meal_time": None,
        "last_sleep_time": None,
        "last_asked_sleep_time": None,
        "last_plan_time": None,
        "last_plan_desc": None,
        "last_asked_plan_time": None,
        "today_context": {
            "variable_event": None,
            "availability_now": "free",
            "ping_count_today": 0,
            "last_proactive_at": None,
            "proactive_count_today": 0,
        },
        "topic_memory": {
            "last_topic": None,
            "topic_repeat_count": 0,
            "last_recall_fact_ids": [],
        },
        "flags": {
            "soft_distance_until": None,
            "post_transition_until": None,
        },
        "user_preferences": {
            "likes": [],
            "dislikes": [],
            "last_asked_pref_at": None,
        },
    }


class MemoryStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_state (user_id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            conn.commit()

    def load(self, user_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM memory_state WHERE user_id = ?", (user_id,)
            ).fetchone()
        if not row:
            return default_state()
        state = json.loads(row[0])
        return self._merge_defaults(state)

    def save(self, user_id: str, state: Dict[str, Any]) -> None:
        payload = json.dumps(state, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO memory_state (user_id, data) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET data = excluded.data",
                (user_id, payload),
            )
            conn.commit()

    def list_user_ids(self) -> List[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT user_id FROM memory_state").fetchall()
        return [row[0] for row in rows]

    @staticmethod
    def _merge_defaults(state: Dict[str, Any]) -> Dict[str, Any]:
        merged = default_state()
        for key, value in state.items():
            if isinstance(value, dict) and key in merged:
                merged[key].update(value)
            else:
                merged[key] = value
        return merged
