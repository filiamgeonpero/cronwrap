"""Circuit breaker for cron jobs — stops firing a job when it fails too many times."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from cronwrap.history import JobHistory


@dataclass
class CircuitBreakerConfig:
    enabled: bool = False
    failure_threshold: int = 3   # consecutive failures before opening
    recovery_timeout: int = 300  # seconds before attempting half-open

    @property
    def is_enabled(self) -> bool:
        return self.enabled and self.failure_threshold > 0


def consecutive_failures(job_name: str, history: JobHistory) -> int:
    """Return the number of consecutive failures at the tail of the history."""
    records = history.recent(job_name, limit=50)
    count = 0
    for record in reversed(records):
        if record.exit_code != 0:
            count += 1
        else:
            break
    return count


def last_failure_age(job_name: str, history: JobHistory) -> Optional[float]:
    """Return seconds since the most recent failure, or None if no failures."""
    records = history.recent(job_name, limit=50)
    for record in reversed(records):
        if record.exit_code != 0 and record.finished_at is not None:
            return time.time() - record.finished_at
    return None


def is_open(job_name: str, cfg: CircuitBreakerConfig, history: JobHistory) -> bool:
    """Return True when the circuit is open (job should be skipped)."""
    if not cfg.is_enabled:
        return False
    failures = consecutive_failures(job_name, history)
    if failures < cfg.failure_threshold:
        return False
    age = last_failure_age(job_name, history)
    if age is None:
        return False
    # Still within recovery timeout — circuit remains open
    return age < cfg.recovery_timeout


def seconds_until_recovery(job_name: str, cfg: CircuitBreakerConfig, history: JobHistory) -> Optional[float]:
    """Return seconds remaining until the circuit may attempt recovery, or None."""
    if not is_open(job_name, cfg, history):
        return None
    age = last_failure_age(job_name, history)
    if age is None:
        return None
    remaining = cfg.recovery_timeout - age
    return max(0.0, remaining)
