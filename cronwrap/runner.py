"""Job runner — executes a command with timeout, retry, logging, and alerting."""

import subprocess
import time
import logging
from typing import Optional

from cronwrap.config import JobConfig
from cronwrap.alerts import (
    build_failure_message,
    build_timeout_message,
    send_email_alert,
)

log = logging.getLogger(__name__)


def run_job(config: JobConfig) -> int:
    """
    Execute the job defined in *config*.

    Handles:
    - Timeout enforcement
    - Retry logic with configurable delay
    - Email alerts on failure / timeout

    Returns the final exit code (0 on success).
    """
    attempt = 0
    max_attempts = config.retries + 1
    last_exit_code = -1

    while attempt < max_attempts:
        attempt += 1
        log.info(
            "[%s] Starting attempt %d/%d: %s",
            config.job_name, attempt, max_attempts, config.command,
        )

        exit_code, stderr = _execute(config.command, config.timeout, config.job_name)

        if exit_code is None:
            # Timeout occurred
            log.error("[%s] Timed out after %ds.", config.job_name, config.timeout)
            if config.alert_on_timeout:
                _send_timeout_alert(config)
            last_exit_code = 124  # conventional timeout exit code
            break

        last_exit_code = exit_code
        if exit_code == 0:
            log.info("[%s] Completed successfully.", config.job_name)
            return 0

        log.warning(
            "[%s] Attempt %d failed with exit code %d.",
            config.job_name, attempt, exit_code,
        )

        if attempt < max_attempts:
            log.info("[%s] Retrying in %ds…", config.job_name, config.retry_delay)
            time.sleep(config.retry_delay)

    if last_exit_code != 0 and config.alert_on_failure:
        _send_failure_alert(config, last_exit_code, "")

    return last_exit_code


def _execute(command: str, timeout: Optional[int], job_name: str):
    """
    Run *command* in a subprocess.

    Returns ``(exit_code, stderr)`` on completion, or ``(None, '')`` on timeout.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stderr
    except subprocess.TimeoutExpired:
        return None, ""


def _send_failure_alert(config: JobConfig, exit_code: int, stderr: str) -> None:
    body = build_failure_message(config.job_name, exit_code, stderr)
    send_email_alert(
        subject=f"[cronwrap] FAILED: {config.job_name}",
        body=body,
        config=config.alert_config,
    )


def _send_timeout_alert(config: JobConfig) -> None:
    body = build_timeout_message(config.job_name, config.timeout or 0)
    send_email_alert(
        subject=f"[cronwrap] TIMEOUT: {config.job_name}",
        body=body,
        config=config.alert_config,
    )
