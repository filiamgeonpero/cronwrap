"""Timeout enforcement for cron job execution."""

import signal
import functools
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional


class TimeoutExpired(Exception):
    """Raised when a job exceeds its allowed execution time."""

    def __init__(self, job_name: str, seconds: int):
        self.job_name = job_name
        self.seconds = seconds
        super().__init__(
            f"Job '{job_name}' timed out after {seconds} second(s)."
        )


@dataclass
class TimeoutConfig:
    """Configuration for job timeout behaviour."""

    seconds: int = 0          # 0 means no timeout
    kill_on_timeout: bool = True

    @property
    def enabled(self) -> bool:
        return self.seconds > 0


def _alarm_handler(signum, frame):
    raise TimeoutExpired.__new__(TimeoutExpired)  # filled in by context manager


@contextmanager
def enforce_timeout(config: TimeoutConfig, job_name: str = "unknown"):
    """Context manager that raises TimeoutExpired if the block runs too long.

    Only works on Unix (uses SIGALRM).  On platforms without SIGALRM the
    context manager is a no-op so code remains portable.
    """
    if not config.enabled or not hasattr(signal, "SIGALRM"):
        yield
        return

    original_handler = signal.signal(signal.SIGALRM, _make_handler(job_name, config.seconds))
    signal.alarm(config.seconds)
    try:
        yield
    except TimeoutExpired:
        raise
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


def _make_handler(job_name: str, seconds: int):
    """Return a SIGALRM handler that raises TimeoutExpired with context."""
    def _handler(signum, frame):
        raise TimeoutExpired(job_name, seconds)
    return _handler


def timeout_for_config(raw: dict) -> TimeoutConfig:
    """Build a TimeoutConfig from a raw config dict (e.g. loaded from TOML)."""
    timeout_section = raw.get("timeout", {})
    if isinstance(timeout_section, int):
        return TimeoutConfig(seconds=timeout_section)
    return TimeoutConfig(
        seconds=int(timeout_section.get("seconds", 0)),
        kill_on_timeout=bool(timeout_section.get("kill_on_timeout", True)),
    )
