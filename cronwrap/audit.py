"""Audit trail: persist and query structured run events for a job."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

_DEFAULT_DB = Path.home() / ".cronwrap" / "audit.db"


@dataclass
class AuditEvent:
    job_name: str
    event_type: str          # "start" | "success" | "failure" | "timeout" | "retry"
    timestamp: str
    detail: Optional[str] = None
    exit_code: Optional[int] = None
    attempt: int = 1


class AuditLog:
    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        self._db_path = db_path
        self._conn = self._connect()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self._db_path), check_same_thread=False)

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name  TEXT    NOT NULL,
                event_type TEXT   NOT NULL,
                timestamp TEXT    NOT NULL,
                detail    TEXT,
                exit_code INTEGER,
                attempt   INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        self._conn.commit()

    def record(self, event: AuditEvent) -> int:
        cur = self._conn.execute(
            "INSERT INTO audit_events "
            "(job_name, event_type, timestamp, detail, exit_code, attempt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                event.job_name,
                event.event_type,
                event.timestamp,
                event.detail,
                event.exit_code,
                event.attempt,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def query(
        self,
        job_name: str,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[AuditEvent]:
        sql = "SELECT job_name, event_type, timestamp, detail, exit_code, attempt "\
              "FROM audit_events WHERE job_name = ?"
        params: list = [job_name]
        if event_type:
            sql += " AND event_type = ?"
            params.append(event_type)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [AuditEvent(*row) for row in rows]

    def close(self) -> None:
        self._conn.close()


def make_event(
    job_name: str,
    event_type: str,
    detail: Optional[str] = None,
    exit_code: Optional[int] = None,
    attempt: int = 1,
) -> AuditEvent:
    return AuditEvent(
        job_name=job_name,
        event_type=event_type,
        timestamp=datetime.utcnow().isoformat(timespec="seconds"),
        detail=detail,
        exit_code=exit_code,
        attempt=attempt,
    )
