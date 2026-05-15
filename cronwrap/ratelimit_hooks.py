"""Hooks that integrate rate limiting with the job runner."""

from __future__ import annotations

import logging
from typing import Optional

from cronwrap.history import JobHistory
from cronwrap.ratelimit import RateLimitConfig, is_rate_limited, runs_remaining

logger = logging.getLogger(__name__)


def gate_on_rate_limit(
    history: JobHistory,
    job_name: str,
    config: Optional[RateLimitConfig],
) -> bool:
    """Return True (allow run) or False (blocked by rate limit).

    Logs a warning when the job is blocked.
    """
    if config is None or not config.enabled:
        return True

    if is_rate_limited(history, job_name, config):
        logger.warning(
            "job '%s' is rate-limited: reached %d runs in %ds window",
            job_name,
            config.max_runs,
            config.window_seconds,
        )
        return False

    remaining = runs_remaining(history, job_name, config)
    logger.debug(
        "job '%s' rate-limit check passed: %d run(s) remaining in window",
        job_name,
        remaining,
    )
    return True


def log_rate_limit_skip(job_name: str, config: RateLimitConfig) -> None:
    """Emit a structured log entry when a job execution is skipped due to rate limiting."""
    logger.info(
        "skipping job '%s': rate limit of %d/%ds exceeded",
        job_name,
        config.max_runs,
        config.window_seconds,
    )
