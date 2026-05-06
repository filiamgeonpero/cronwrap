"""Configuration loader for cronwrap jobs."""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, List

from cronwrap.alerts import AlertConfig


@dataclass
class JobConfig:
    """Full configuration for a single cron job wrapper invocation."""
    command: str
    job_name: str = "cron_job"
    timeout: Optional[int] = None          # seconds; None means no limit
    retries: int = 0
    retry_delay: int = 5                   # seconds between retries
    log_dir: str = "/var/log/cronwrap"
    alert_on_failure: bool = False
    alert_on_timeout: bool = False
    alert_config: AlertConfig = field(default_factory=AlertConfig)


def load_config(path: str) -> JobConfig:
    """
    Load a JobConfig from a JSON file.

    Expected JSON keys mirror JobConfig fields.  The optional nested
    ``alert_config`` key maps to AlertConfig fields.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    alert_data = data.pop("alert_config", {})
    alert_cfg = AlertConfig(**alert_data) if alert_data else AlertConfig()

    return JobConfig(alert_config=alert_cfg, **data)


def config_from_env(command: str) -> JobConfig:
    """
    Build a JobConfig from environment variables, falling back to defaults.

    Recognised variables (all prefixed ``CRONWRAP_``):
      JOB_NAME, TIMEOUT, RETRIES, RETRY_DELAY, LOG_DIR,
      ALERT_ON_FAILURE, ALERT_ON_TIMEOUT,
      SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
      ALERT_FROM, ALERT_RECIPIENTS (comma-separated)
    """
    def _bool(key: str, default: bool = False) -> bool:
        return os.environ.get(key, str(default)).lower() in ("1", "true", "yes")

    recipients_raw = os.environ.get("CRONWRAP_ALERT_RECIPIENTS", "")
    recipients: List[str] = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    alert_cfg = AlertConfig(
        smtp_host=os.environ.get("CRONWRAP_SMTP_HOST", "localhost"),
        smtp_port=int(os.environ.get("CRONWRAP_SMTP_PORT", "25")),
        smtp_user=os.environ.get("CRONWRAP_SMTP_USER"),
        smtp_password=os.environ.get("CRONWRAP_SMTP_PASSWORD"),
        from_address=os.environ.get("CRONWRAP_ALERT_FROM", "cronwrap@localhost"),
        recipients=recipients,
    )

    timeout_raw = os.environ.get("CRONWRAP_TIMEOUT")
    return JobConfig(
        command=command,
        job_name=os.environ.get("CRONWRAP_JOB_NAME", "cron_job"),
        timeout=int(timeout_raw) if timeout_raw else None,
        retries=int(os.environ.get("CRONWRAP_RETRIES", "0")),
        retry_delay=int(os.environ.get("CRONWRAP_RETRY_DELAY", "5")),
        log_dir=os.environ.get("CRONWRAP_LOG_DIR", "/var/log/cronwrap"),
        alert_on_failure=_bool("CRONWRAP_ALERT_ON_FAILURE"),
        alert_on_timeout=_bool("CRONWRAP_ALERT_ON_TIMEOUT"),
        alert_config=alert_cfg,
    )
