"""Configuration loading for cronwrap jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes")


@dataclass
class AlertConfig:
    enabled: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 587
    from_addr: str = ""
    to_addrs: list[str] = field(default_factory=list)


@dataclass
class JobConfig:
    name: str = ""
    command: str = ""
    timeout: int = 0
    retries: int = 0
    schedule: Optional[str] = None  # NEW: optional cron expression
    alert: AlertConfig = field(default_factory=AlertConfig)


def load_config(path: str) -> JobConfig:
    """Load a JobConfig from a TOML file at *path*."""
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    alert_data = data.get("alert", {})
    alert = AlertConfig(
        enabled=_bool(alert_data.get("enabled", False)),
        smtp_host=alert_data.get("smtp_host", "localhost"),
        smtp_port=int(alert_data.get("smtp_port", 587)),
        from_addr=alert_data.get("from_addr", ""),
        to_addrs=alert_data.get("to_addrs", []),
    )
    return JobConfig(
        name=data.get("name", ""),
        command=data.get("command", ""),
        timeout=int(data.get("timeout", 0)),
        retries=int(data.get("retries", 0)),
        schedule=data.get("schedule"),
        alert=alert,
    )


def config_from_env() -> JobConfig:
    """Build a JobConfig from environment variables."""
    alert = AlertConfig(
        enabled=_bool(os.getenv("CW_ALERT_ENABLED", "false")),
        smtp_host=os.getenv("CW_SMTP_HOST", "localhost"),
        smtp_port=int(os.getenv("CW_SMTP_PORT", "587")),
        from_addr=os.getenv("CW_FROM_ADDR", ""),
        to_addrs=[
            a.strip()
            for a in os.getenv("CW_TO_ADDRS", "").split(",")
            if a.strip()
        ],
    )
    return JobConfig(
        name=os.getenv("CW_JOB_NAME", ""),
        command=os.getenv("CW_COMMAND", ""),
        timeout=int(os.getenv("CW_TIMEOUT", "0")),
        retries=int(os.getenv("CW_RETRIES", "0")),
        schedule=os.getenv("CW_SCHEDULE"),
        alert=alert,
    )
