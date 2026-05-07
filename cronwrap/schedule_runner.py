"""High-level schedule loop with optional per-job throttling."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from cronwrap.scheduler import is_due
from cronwrap.throttle import ThrottleConfig, is_throttled

logger = logging.getLogger(__name__)


def tick(
    jobs: List[Dict[str, Any]],
    now: time.struct_time,
    history=None,
) -> List[str]:
    """Evaluate all jobs against *now* and return names of triggered jobs.

    A job dict may contain:
      - ``name`` (str, required)
      - ``schedule`` (str, optional cron expression)
      - ``throttle`` (ThrottleConfig, optional)
      - ``run`` (callable, optional — called when the job is triggered)

    Args:
        jobs: List of job configuration dicts.
        now: The current time as a struct_time.
        history: A JobHistory instance used for throttle checks (optional).

    Returns:
        Names of jobs that were triggered in this tick.
    """
    triggered: List[str] = []

    for job in jobs:
        name: str = job.get("name", "<unnamed>")
        schedule: str | None = job.get("schedule")

        if not schedule:
            logger.debug("Job %s has no schedule — skipping.", name)
            continue

        if not is_due(schedule, now):
            continue

        throttle: ThrottleConfig | None = job.get("throttle")
        if throttle and history and is_throttled(name, throttle, history):
            logger.info("Job %s is throttled — skipping this tick.", name)
            continue

        triggered.append(name)
        runner = job.get("run")
        if callable(runner):
            try:
                runner()
            except Exception:
                logger.exception("Job %s raised an exception during tick.", name)

    return triggered


def run_loop(
    jobs: List[Dict[str, Any]],
    interval: float = 60.0,
    history=None,
) -> None:  # pragma: no cover
    """Block forever, calling :func:`tick` every *interval* seconds."""
    logger.info("Starting schedule loop (interval=%.1fs, jobs=%d).", interval, len(jobs))
    while True:
        now = time.localtime()
        tick(jobs, now, history=history)
        time.sleep(interval)
