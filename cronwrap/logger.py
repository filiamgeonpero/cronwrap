"""Logging module for cronwrap — captures stdout/stderr and writes structured logs."""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(job_name: str, log_dir: str = "/var/log/cronwrap") -> logging.Logger:
    """Configure and return a logger for the given cron job."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(job_name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # File handler — one log file per job
    file_handler = logging.FileHandler(log_path / f"{job_name}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler for interactive use
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log_execution(logger: logging.Logger, job_name: str, exit_code: int,
                  stdout: str, stderr: str, duration_seconds: float) -> None:
    """Log the result of a cron job execution."""
    status = "SUCCESS" if exit_code == 0 else "FAILURE"
    logger.info(
        "Job finished | status=%s exit_code=%d duration=%.2fs",
        status, exit_code, duration_seconds,
    )
    if stdout.strip():
        for line in stdout.strip().splitlines():
            logger.debug("[stdout] %s", line)
    if stderr.strip():
        for line in stderr.strip().splitlines():
            logger.warning("[stderr] %s", line)
