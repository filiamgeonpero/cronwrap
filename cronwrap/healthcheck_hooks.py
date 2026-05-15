"""Hooks that integrate healthcheck reporting into the job runner pipeline."""
from __future__ import annotations

import logging
from typing import Optional

from cronwrap.healthcheck import HealthStatus, check_health
from cronwrap.history import JobHistory

logger = logging.getLogger(__name__)


def log_health_status(
    job_name: str,
    history: JobHistory,
    max_age_seconds: float = 0,
) -> HealthStatus:
    """Check and log the health status of *job_name* after a run.

    Intended to be called at the end of a job execution so operators can see
    the current health in the log stream without querying the database manually.

    Returns:
        The computed HealthStatus (callers may inspect it further).
    """
    status = check_health(job_name, history, max_age_seconds=max_age_seconds)
    if status.healthy:
        logger.info(
            "[healthcheck] job=%s status=ok last_success_ts=%s",
            job_name,
            status.last_success_ts,
        )
    else:
        logger.warning(
            "[healthcheck] job=%s status=FAIL message=%s",
            job_name,
            status.message,
        )
    return status


def assert_healthy(
    job_name: str,
    history: JobHistory,
    max_age_seconds: float = 0,
) -> None:
    """Raise RuntimeError if the job is not healthy.

    Useful as a pre-flight check before launching a dependent job: ensures the
    upstream job has a recent successful run before proceeding.

    Raises:
        RuntimeError: when the job is considered unhealthy.
    """
    status = check_health(job_name, history, max_age_seconds=max_age_seconds)
    if not status.healthy:
        raise RuntimeError(
            f"healthcheck failed for job '{job_name}': {status.message}"
        )
    logger.debug(
        "[healthcheck] pre-flight ok for job=%s", job_name
    )
