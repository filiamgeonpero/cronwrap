"""Integration helpers: emit AuditEvents from runner and retry callbacks."""

from __future__ import annotations

from typing import Callable, Optional

from cronwrap.audit import AuditLog, make_event


def on_start(log: AuditLog, job_name: str, attempt: int = 1) -> None:
    """Record that a job execution has begun."""
    log.record(make_event(job_name, "start", attempt=attempt))


def on_success(
    log: AuditLog,
    job_name: str,
    exit_code: int = 0,
    attempt: int = 1,
) -> None:
    """Record a successful job completion."""
    log.record(
        make_event(job_name, "success", exit_code=exit_code, attempt=attempt)
    )


def on_failure(
    log: AuditLog,
    job_name: str,
    exit_code: Optional[int],
    detail: Optional[str] = None,
    attempt: int = 1,
) -> None:
    """Record a failed job execution."""
    log.record(
        make_event(
            job_name,
            "failure",
            detail=detail,
            exit_code=exit_code,
            attempt=attempt,
        )
    )


def on_timeout(
    log: AuditLog,
    job_name: str,
    detail: Optional[str] = None,
    attempt: int = 1,
) -> None:
    """Record a job that was killed due to timeout."""
    log.record(
        make_event(job_name, "timeout", detail=detail, attempt=attempt)
    )


def on_retry(
    log: AuditLog,
    job_name: str,
    attempt: int,
    reason: Optional[str] = None,
) -> None:
    """Record that a retry is about to be attempted."""
    log.record(
        make_event(job_name, "retry", detail=reason, attempt=attempt)
    )


def make_audit_callbacks(log: AuditLog, job_name: str) -> dict:
    """Return a dict of named callbacks suitable for passing to run_job/with_retry."""
    return {
        "on_start": lambda attempt=1: on_start(log, job_name, attempt=attempt),
        "on_success": lambda exit_code=0, attempt=1: on_success(
            log, job_name, exit_code=exit_code, attempt=attempt
        ),
        "on_failure": lambda exit_code=None, detail=None, attempt=1: on_failure(
            log, job_name, exit_code=exit_code, detail=detail, attempt=attempt
        ),
        "on_timeout": lambda detail=None, attempt=1: on_timeout(
            log, job_name, detail=detail, attempt=attempt
        ),
        "on_retry": lambda attempt, reason=None: on_retry(
            log, job_name, attempt=attempt, reason=reason
        ),
    }
