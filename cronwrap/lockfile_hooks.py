"""Integration hooks that gate job execution via lockfiles."""

import logging
from typing import Optional, Callable

from cronwrap.lockfile import LockConfig, LockAcquireError, acquire_lock, release_lock

logger = logging.getLogger(__name__)


def gate_on_lock(
    job_name: str,
    config: Optional[LockConfig],
    run_fn: Callable[[], int],
) -> int:
    """Acquire the lockfile, run *run_fn*, then release the lock.

    Returns the exit code returned by *run_fn*, or 1 if the lock
    could not be acquired.
    """
    if config is None or not config.enabled:
        return run_fn()

    try:
        lock_path = acquire_lock(job_name, config)
    except LockAcquireError as exc:
        log_lock_skip(job_name, str(exc))
        return 1

    try:
        return run_fn()
    finally:
        release_lock(job_name, config)
        if lock_path:
            logger.debug("cronwrap.lockfile: released lock for '%s'", job_name)


def log_lock_skip(job_name: str, reason: str) -> None:
    """Emit a structured warning when a job is skipped due to locking."""
    logger.warning(
        "cronwrap.lockfile: skipping job '%s' — %s",
        job_name,
        reason,
    )
