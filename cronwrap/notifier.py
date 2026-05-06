"""Slack and webhook notification support for cronwrap."""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    url: str
    timeout: int = 10
    headers: dict = field(default_factory=lambda: {"Content-Type": "application/json"})


def build_slack_payload(job_name: str, message: str, success: bool) -> dict:
    """Build a Slack-compatible webhook payload."""
    color = "#36a64f" if success else "#ff0000"
    status = "succeeded" if success else "failed"
    return {
        "attachments": [
            {
                "color": color,
                "title": f"Cron job *{job_name}* {status}",
                "text": message,
                "footer": "cronwrap",
            }
        ]
    }


def send_webhook(
    config: WebhookConfig,
    payload: dict,
) -> bool:
    """Send a JSON payload to a webhook URL.

    Returns True on success, False on failure.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        config.url,
        data=data,
        headers=config.headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            status = resp.getcode()
            if status == 200:
                logger.debug("Webhook notification sent successfully.")
                return True
            logger.warning("Webhook responded with status %s", status)
            return False
    except urllib.error.URLError as exc:
        logger.error("Failed to send webhook notification: %s", exc)
        return False


def notify(
    webhook_url: str,
    job_name: str,
    message: str,
    success: bool = False,
    timeout: int = 10,
) -> bool:
    """High-level helper to send a Slack-style webhook notification."""
    config = WebhookConfig(url=webhook_url, timeout=timeout)
    payload = build_slack_payload(job_name, message, success)
    return send_webhook(config, payload)
