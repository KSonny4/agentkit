"""Mailbox — SQLite-backed task queue."""

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class TaskStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class Mailbox:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._migrate()

    def _migrate(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def enqueue(self, content: str, source: str) -> int:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            cursor = self.conn.execute(
                "INSERT INTO tasks (content, source, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (content, source, TaskStatus.PENDING, now, now),
            )
            self.conn.commit()
            return cursor.lastrowid

    def dequeue(self) -> dict | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT * FROM tasks WHERE status = ? ORDER BY id ASC LIMIT 1",
                (TaskStatus.PENDING,),
            ).fetchone()
            if row is None:
                return None

            task = dict(row)
            now = datetime.now(timezone.utc).isoformat()
            self.conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                (TaskStatus.PROCESSING, now, task["id"]),
            )
            self.conn.commit()
            task["status"] = TaskStatus.PROCESSING
            task["updated_at"] = now
            return task

    def complete(self, task_id: int, result: str = "") -> None:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self.conn.execute(
                "UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?",
                (TaskStatus.DONE, result, now, task_id),
            )
            self.conn.commit()

    def fail(self, task_id: int, error: str = "") -> None:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self.conn.execute(
                "UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?",
                (TaskStatus.FAILED, error, now, task_id),
            )
            self.conn.commit()

    def history(self, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM tasks ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
