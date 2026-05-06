"""Tests for cronwrap.alerts."""

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.alerts import (
    AlertConfig,
    build_failure_message,
    build_timeout_message,
    send_email_alert,
)


# ---------------------------------------------------------------------------
# AlertConfig
# ---------------------------------------------------------------------------

class TestAlertConfig:
    def test_defaults(self):
        cfg = AlertConfig()
        assert cfg.smtp_host == "localhost"
        assert cfg.smtp_port == 25
        assert cfg.recipients == []
        assert cfg.use_tls is False

    def test_custom_values(self):
        cfg = AlertConfig(
            smtp_host="mail.example.com",
            smtp_port=587,
            recipients=["ops@example.com"],
            use_tls=True,
        )
        assert cfg.smtp_host == "mail.example.com"
        assert cfg.smtp_port == 587
        assert "ops@example.com" in cfg.recipients


# ---------------------------------------------------------------------------
# Message builders
# ---------------------------------------------------------------------------

def test_build_failure_message_contains_job_name():
    msg = build_failure_message("my_job", 1, "some error")
    assert "my_job" in msg
    assert "1" in msg
    assert "some error" in msg


def test_build_failure_message_no_stderr():
    msg = build_failure_message("my_job", 2, "")
    assert "(none)" in msg


def test_build_timeout_message():
    msg = build_timeout_message("slow_job", 30)
    assert "slow_job" in msg
    assert "30" in msg


# ---------------------------------------------------------------------------
# send_email_alert
# ---------------------------------------------------------------------------

class TestSendEmailAlert:
    def _cfg(self, recipients=None):
        return AlertConfig(
            smtp_host="localhost",
            smtp_port=25,
            recipients=recipients or ["admin@example.com"],
        )

    def test_returns_false_with_no_recipients(self):
        result = send_email_alert("subject", "body", AlertConfig())
        assert result is False

    @patch("cronwrap.alerts.smtplib.SMTP")
    def test_sends_mail_successfully(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        result = send_email_alert("Alert", "Something failed.", self._cfg())

        assert result is True
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

    @patch("cronwrap.alerts.smtplib.SMTP", side_effect=smtplib.SMTPException("conn refused"))
    def test_returns_false_on_smtp_error(self, _mock):
        result = send_email_alert("Alert", "body", self._cfg())
        assert result is False

    @patch("cronwrap.alerts.smtplib.SMTP")
    def test_uses_tls_when_configured(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server
        cfg = AlertConfig(recipients=["a@b.com"], use_tls=True)

        send_email_alert("s", "b", cfg)
        mock_server.starttls.assert_called_once()
