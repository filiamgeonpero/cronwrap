"""High-level scheduler that checks which configured jobs are due and runs them."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Iterable

from cronwrap.config import JobConfig
from cronwrap.runner import run_job
from cronwrap.scheduler import is_due

log = logging.getLogger(__name__)


def tick(jobs: Iterable[JobConfig], now: datetime | None = None) -> list[str]:
    """Check each job and run those whose cron expression is currently due.

    Returns a list of job names that were triggered.
    """
    triggered: list[str] = []
    now = now or datetime.now()
    for job in jobs:
        expression: str | None = getattr(job, "schedule", None)
        if not expression:
            log.debug("Job %r has no schedule, skipping.", job.name)
            continue
        try:
            due = is_due(expression, now=now)
        except ValueError as exc:
            log.error("Invalid cron expression for job %r: %s", job.name, exc)
            continue
        if due:
            log.info("Job %r is due — launching.", job.name)
            try:
                run_job(job)
            except Exception as exc:  # noqa: BLE001
                log.error("Job %r raised an unexpected error: %s", job.name, exc)
            triggered.append(job.name)
        else:
            log.debug("Job %r is not due at %s.", job.name, now.strftime("%H:%M"))
    return triggered


def run_loop(jobs: Iterable[JobConfig], interval: int = 60) -> None:  # pragma: no cover
    """Block forever, calling *tick* once per *interval* seconds.

    Aligns wakeups to the top of each minute so jobs fire on schedule.
    """
    jobs = list(jobs)
    log.info("Schedule runner started with %d job(s).", len(jobs))
    while True:
        tick(jobs)
        now = time.time()
        sleep_for = interval - (now % interval)
        time.sleep(sleep_for)
