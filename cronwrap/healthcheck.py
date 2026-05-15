"""Healthcheck endpoint support for cron job monitoring."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.history import JobHistory


@dataclass
class HealthStatus:
    job_name: str
    healthy: bool
    last_success_ts: Optional[float]
    last_exit_code: Optional[int]
    message: str


def _last_record(history: JobHistory, job_name: str):
    """Return the most recent execution record for *job_name*, or None."""
    records = history.query(job_name, limit=1)
    return records[0] if records else None


def check_health(
    job_name: str,
    history: JobHistory,
    max_age_seconds: float = 0,
) -> HealthStatus:
    """Return a HealthStatus for *job_name*.

    Args:
        job_name: The name of the job to inspect.
        history: A JobHistory instance to query.
        max_age_seconds: If > 0, the job is considered unhealthy when the last
            successful run finished more than this many seconds ago.
    """
    record = _last_record(history, job_name)

    if record is None:
        return HealthStatus(
            job_name=job_name,
            healthy=False,
            last_success_ts=None,
            last_exit_code=None,
            message="no execution history found",
        )

    last_exit = record.exit_code
    last_success_ts: Optional[float] = None

    # Walk history to find last success
    for r in history.query(job_name, limit=100):
        if r.exit_code == 0 and r.finished_at is not None:
            last_success_ts = r.finished_at
            break

    if last_success_ts is None:
        return HealthStatus(
            job_name=job_name,
            healthy=False,
            last_success_ts=None,
            last_exit_code=last_exit,
            message="no successful run recorded",
        )

    if max_age_seconds > 0:
        age = time.time() - last_success_ts
        if age > max_age_seconds:
            return HealthStatus(
                job_name=job_name,
                healthy=False,
                last_success_ts=last_success_ts,
                last_exit_code=last_exit,
                message=f"last success was {age:.0f}s ago (limit {max_age_seconds:.0f}s)",
            )

    return HealthStatus(
        job_name=job_name,
        healthy=True,
        last_success_ts=last_success_ts,
        last_exit_code=last_exit,
        message="ok",
    )


def render_health(statuses: list[HealthStatus]) -> str:
    """Render a list of HealthStatus objects as a human-readable table."""
    lines = [f"{'JOB':<30} {'STATUS':<10} MESSAGE"]
    lines.append("-" * 70)
    for s in statuses:
        status = "OK" if s.healthy else "FAIL"
        lines.append(f"{s.job_name:<30} {status:<10} {s.message}")
    return "\n".join(lines)
