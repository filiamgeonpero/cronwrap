"""High-level hooks that integrate concurrency limiting into the run pipeline."""

from __future__ import annotations

import logging
import os
from typing import Optional

from cronwrap.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimitError,
    check_concurrency,
    deregister_run,
    register_run,
)

logger = logging.getLogger(__name__)


def gate_on_concurrency(
    job_name: str,
    cfg: Optional[ConcurrencyConfig],
) -> Optional[int]:
    """Check concurrency limit before a job runs.

    Returns the *run_id* that must be passed to :func:`release_concurrency_slot`
    when the job finishes, or ``None`` if concurrency limiting is disabled.

    Raises :class:`ConcurrencyLimitError` when the limit is exceeded.
    """
    if cfg is None or not cfg.enabled:
        return None

    check_concurrency(job_name, cfg)  # raises if at limit
    run_id = register_run(job_name, os.getpid(), cfg.db_path)
    logger.debug(
        "Concurrency slot acquired for '%s' (run_id=%d, pid=%d).",
        job_name,
        run_id,
        os.getpid(),
    )
    return run_id


def release_concurrency_slot(
    job_name: str,
    run_id: Optional[int],
    cfg: Optional[ConcurrencyConfig],
) -> None:
    """Release a previously acquired concurrency slot."""
    if run_id is None or cfg is None:
        return
    deregister_run(run_id, cfg.db_path)
    logger.debug("Concurrency slot released for '%s' (run_id=%d).", job_name, run_id)


def log_concurrency_skip(job_name: str, exc: ConcurrencyLimitError) -> None:
    """Emit a structured warning when a job is skipped due to concurrency."""
    logger.warning(
        "Skipping job '%s': concurrency limit reached — %s",
        job_name,
        exc,
    )
