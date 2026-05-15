"""Concurrency limiting for cron jobs.

Prevents more than N instances of a job from running simultaneously
by tracking active runs in a shared SQLite table.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ConcurrencyConfig:
    max_instances: int = 1
    db_path: str = "/tmp/cronwrap_concurrency.db"

    @property
    def enabled(self) -> bool:
        return self.max_instances > 0


class ConcurrencyLimitError(RuntimeError):
    """Raised when the concurrency limit is reached."""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=5)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS active_runs ("
        "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "  job_name TEXT NOT NULL,"
        "  pid INTEGER NOT NULL,"
        "  started_at REAL NOT NULL"
        ")"
    )
    conn.commit()
    return conn


def active_count(job_name: str, db_path: str) -> int:
    """Return number of currently registered active runs for *job_name*."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM active_runs WHERE job_name = ?", (job_name,)
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def register_run(job_name: str, pid: int, db_path: str) -> int:
    """Register an active run; return the row id."""
    conn = _connect(db_path)
    try:
        cur = conn.execute(
            "INSERT INTO active_runs (job_name, pid, started_at) VALUES (?, ?, ?)",
            (job_name, pid, time.time()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def deregister_run(run_id: int, db_path: str) -> None:
    """Remove an active run record by *run_id*."""
    conn = _connect(db_path)
    try:
        conn.execute("DELETE FROM active_runs WHERE id = ?", (run_id,))
        conn.commit()
    finally:
        conn.close()


def check_concurrency(job_name: str, cfg: ConcurrencyConfig) -> None:
    """Raise *ConcurrencyLimitError* if the limit is already reached."""
    if not cfg.enabled:
        return
    count = active_count(job_name, cfg.db_path)
    if count >= cfg.max_instances:
        raise ConcurrencyLimitError(
            f"Job '{job_name}' already has {count} active instance(s) "
            f"(limit={cfg.max_instances})."
        )
