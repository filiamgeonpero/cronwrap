"""Lockfile support to prevent overlapping cron job executions."""

import os
import errno
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LockConfig:
    enabled: bool = True
    lock_dir: str = "/tmp/cronwrap/locks"
    timeout_seconds: int = 0  # 0 = no stale-lock removal


class LockAcquireError(Exception):
    """Raised when a lock cannot be acquired."""


def _lock_path(lock_dir: str, job_name: str) -> str:
    safe = job_name.replace(os.sep, "_").replace(" ", "_")
    return os.path.join(lock_dir, f"{safe}.lock")


def acquire_lock(job_name: str, config: Optional[LockConfig] = None) -> str:
    """Write a PID lockfile. Returns the lock path on success.

    Raises LockAcquireError if another process holds the lock.
    """
    cfg = config or LockConfig()
    if not cfg.enabled:
        return ""

    os.makedirs(cfg.lock_dir, exist_ok=True)
    path = _lock_path(cfg.lock_dir, job_name)

    if os.path.exists(path):
        with open(path) as fh:
            raw = fh.read().strip()
        pid = int(raw) if raw.isdigit() else None
        if pid is not None:
            try:
                os.kill(pid, 0)  # signal 0 = existence check
                raise LockAcquireError(
                    f"Job '{job_name}' is already running (pid {pid})"
                )
            except OSError as exc:
                if exc.errno != errno.ESRCH:
                    raise
                # stale lock — previous process is gone, remove it

    with open(path, "w") as fh:
        fh.write(str(os.getpid()))
    return path


def release_lock(job_name: str, config: Optional[LockConfig] = None) -> None:
    """Remove the PID lockfile for *job_name* if it belongs to this process."""
    cfg = config or LockConfig()
    if not cfg.enabled:
        return

    path = _lock_path(cfg.lock_dir, job_name)
    if not os.path.exists(path):
        return

    with open(path) as fh:
        raw = fh.read().strip()
    if raw == str(os.getpid()):
        os.remove(path)


def is_locked(job_name: str, config: Optional[LockConfig] = None) -> bool:
    """Return True if a live process holds the lock for *job_name*."""
    cfg = config or LockConfig()
    path = _lock_path(cfg.lock_dir, job_name)
    if not os.path.exists(path):
        return False
    with open(path) as fh:
        raw = fh.read().strip()
    pid = int(raw) if raw.isdigit() else None
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
