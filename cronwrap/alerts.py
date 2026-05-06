"""Alerting module for cronwrap — sends notifications on job failure or timeout."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class AlertConfig:
    """Configuration for alert delivery."""
    smtp_host: str = "localhost"
    smtp_port: int = 25
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    use_tls: bool = False
    from_address: str = "cronwrap@localhost"
    recipients: List[str] = field(default_factory=list)


def send_email_alert(
    subject: str,
    body: str,
    config: AlertConfig,
) -> bool:
    """
    Send an email alert using the provided AlertConfig.

    Returns True if the message was sent successfully, False otherwise.
    """
    if not config.recipients:
        logger.warning("No recipients configured; skipping alert.")
        return False

    msg = MIMEMultipart()
    msg["From"] = config.from_address
    msg["To"] = ", ".join(config.recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        if config.use_tls:
            server = smtplib.SMTP(config.smtp_host, config.smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP(config.smtp_host, config.smtp_port)

        if config.smtp_user and config.smtp_password:
            server.login(config.smtp_user, config.smtp_password)

        server.sendmail(config.from_address, config.recipients, msg.as_string())
        server.quit()
        logger.info("Alert sent to %s", config.recipients)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send alert: %s", exc)
        return False


def build_failure_message(job_name: str, exit_code: int, stderr: str) -> str:
    """Build a human-readable failure alert body."""
    return (
        f"Cron job '{job_name}' failed.\n"
        f"Exit code: {exit_code}\n\n"
        f"Stderr output:\n{stderr or '(none)'}"
    )


def build_timeout_message(job_name: str, timeout: int) -> str:
    """Build a human-readable timeout alert body."""
    return (
        f"Cron job '{job_name}' timed out after {timeout} second(s) "
        f"and was terminated."
    )
