"""Hooks that integrate the circuit breaker into the job execution pipeline."""
from __future__ import annotations

import logging
from typing import Optional

from cronwrap.circuit_breaker import CircuitBreakerConfig, is_open, seconds_until_recovery
from cronwrap.history import JobHistory

logger = logging.getLogger(__name__)


def gate_on_circuit_breaker(
    job_name: str,
    cfg: Optional[CircuitBreakerConfig],
    history: JobHistory,
) -> Optional[str]:
    """Return a skip-reason string if the circuit is open, else None.

    Returning a non-None value signals the caller to skip execution.
    """
    if cfg is None or not cfg.is_enabled:
        return None

    if not is_open(job_name, cfg, history):
        return None

    remaining = seconds_until_recovery(job_name, cfg, history)
    if remaining is not None:
        reason = (
            f"circuit breaker open for '{job_name}': "
            f"{cfg.failure_threshold} consecutive failures; "
            f"recovery in {remaining:.0f}s"
        )
    else:
        reason = (
            f"circuit breaker open for '{job_name}': "
            f"{cfg.failure_threshold} consecutive failures"
        )
    return reason


def log_circuit_breaker_skip(job_name: str, reason: str) -> None:
    """Emit a warning when a job is skipped due to an open circuit."""
    logger.warning("[circuit_breaker] skipping job '%s': %s", job_name, reason)
