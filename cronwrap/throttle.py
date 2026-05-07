"""Throttle / rate-limit helpers for cron jobs.

Prevents a job from running more frequently than a configured minimum
interval, even if the cron schedule would trigger it sooner (e.g. after
a manual retry or a clock skew).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.history import JobHistory


@dataclass
class ThrottleConfig:
    """Configuration for job throttling."""

    min_interval_seconds: int = 0  # 0 means no throttling
    enabled: bool = True


def last_run_seconds_ago(job_name: str, history: JobHistory) -> Optional[float]:
    """Return how many seconds ago the job last *started*, or None if never run."""
    records = history.get_recent(job_name, limit=1)
    if not records:
        return None
    last_started_at: float = records[0].started_at
    return time.time() - last_started_at


def is_throttled(
    job_name: str,
    config: ThrottleConfig,
    history: JobHistory,
) -> bool:
    """Return True if the job should be suppressed due to throttling."""
    if not config.enabled or config.min_interval_seconds <= 0:
        return False

    ago = last_run_seconds_ago(job_name, history)
    if ago is None:
        return False  # Never run before — allow it

    return ago < config.min_interval_seconds


def seconds_until_allowed(
    job_name: str,
    config: ThrottleConfig,
    history: JobHistory,
) -> float:
    """Return seconds remaining before the job is allowed to run again.

    Returns 0.0 if the job is not currently throttled.
    """
    if not is_throttled(job_name, config, history):
        return 0.0

    ago = last_run_seconds_ago(job_name, history)
    if ago is None:
        return 0.0

    return max(0.0, config.min_interval_seconds - ago)
