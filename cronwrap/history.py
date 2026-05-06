"""Job execution history tracking using a simple SQLite backend."""

import sqlite3
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, List

DEFAULT_DB_PATH = os.path.expanduser("~/.cronwrap/history.db")


@dataclass
class ExecutionRecord:
    job_name: str
    command: str
    started_at: str
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    success: bool = False
    duration_seconds: Optional[float] = None
    stderr_snippet: Optional[str] = None
    id: Optional[int] = None


class JobHistory:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_name TEXT NOT NULL,
                    command TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    exit_code INTEGER,
                    success INTEGER DEFAULT 0,
                    duration_seconds REAL,
                    stderr_snippet TEXT
                )
            """)
            conn.commit()

    def record_start(self, job_name: str, command: str) -> int:
        started_at = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO executions (job_name, command, started_at) VALUES (?, ?, ?)",
                (job_name, command, started_at),
            )
            conn.commit()
            return cursor.lastrowid

    def record_finish(
        self,
        record_id: int,
        exit_code: int,
        duration_seconds: float,
        stderr_snippet: Optional[str] = None,
    ) -> None:
        finished_at = datetime.utcnow().isoformat()
        success = 1 if exit_code == 0 else 0
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE executions
                SET finished_at=?, exit_code=?, success=?, duration_seconds=?, stderr_snippet=?
                WHERE id=?
                """,
                (finished_at, exit_code, success, duration_seconds, stderr_snippet, record_id),
            )
            conn.commit()

    def get_recent(self, job_name: str, limit: int = 10) -> List[ExecutionRecord]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM executions WHERE job_name=? ORDER BY started_at DESC LIMIT ?",
                (job_name, limit),
            ).fetchall()
        return [
            ExecutionRecord(
                id=row["id"],
                job_name=row["job_name"],
                command=row["command"],
                started_at=row["started_at"],
                finished_at=row["finished_at"],
                exit_code=row["exit_code"],
                success=bool(row["success"]),
                duration_seconds=row["duration_seconds"],
                stderr_snippet=row["stderr_snippet"],
            )
            for row in rows
        ]

    def last_success(self, job_name: str) -> Optional[ExecutionRecord]:
        records = [
            r for r in self.get_recent(job_name, limit=50) if r.success
        ]
        return records[0] if records else None
