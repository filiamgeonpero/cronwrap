"""Rate limiting for cron jobs — prevents a job from running more than N times
in a sliding time window."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from cronwrap.history import JobHistory


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting a job."""

    max_runs: int = 0          # 0 means disabled
    window_seconds: int = 3600  # default: 1-hour window

    @property
    def enabled(self) -> bool:
        return self.max_runs > 0 and self.window_seconds > 0


def runs_in_window(
    history: JobHistory,
    job_name: str,
    window_seconds: int,
) -> int:
    """Return the number of completed runs (any exit code) within the window."""
    records = history.query(job_name)
    if not records:
        return 0

    now = datetime.now(tz=timezone.utc).timestamp()
    cutoff = now - window_seconds

    count = 0
    for rec in records:
        finished = rec.finished_at
        if finished is not None and finished >= cutoff:
            count += 1
    return count


def is_rate_limited(
    history: JobHistory,
    job_name: str,
    config: RateLimitConfig,
) -> bool:
    """Return True when the job has exhausted its allowed runs in the window."""
    if not config.enabled:
        return False
    used = runs_in_window(history, job_name, config.window_seconds)
    return used >= config.max_runs


def runs_remaining(
    history: JobHistory,
    job_name: str,
    config: RateLimitConfig,
) -> Optional[int]:
    """Return how many runs are still allowed, or None when disabled."""
    if not config.enabled:
        return None
    used = runs_in_window(history, job_name, config.window_seconds)
    return max(0, config.max_runs - used)
