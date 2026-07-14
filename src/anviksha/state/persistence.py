"""SQLite-backed persistent state storage."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from anviksha.state.manager import StateManager, StateTransition
from anviksha.types import ExecutionStatus


class PersistentStateManager(StateManager):
    """State manager that persists transitions to SQLite."""

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._replay_from_db()

    @property
    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self._db_path)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self) -> None:
        path = Path(self._db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS state_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    execution_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    step_id TEXT,
                    payload TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_transitions_execution_id
                ON state_transitions(execution_id)
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _replay_from_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT execution_id, status, timestamp, step_id, payload "
                "FROM state_transitions ORDER BY id"
            ).fetchall()
            for row in rows:
                transition = StateTransition(
                    execution_id=row[0],
                    status=ExecutionStatus(row[1]),
                    timestamp=row[2],
                    step_id=row[3],
                    payload=json.loads(row[4]) if row[4] else None,
                )
                self._items.setdefault(transition.execution_id, []).append(transition)
        finally:
            conn.close()

    def record(self, transition: StateTransition) -> None:
        super().record(transition)
        self._conn.execute(
            """
            INSERT INTO state_transitions (execution_id, status, timestamp, step_id, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                transition.execution_id,
                transition.status.value,
                transition.timestamp,
                transition.step_id,
                json.dumps(transition.payload) if transition.payload is not None else None,
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None
