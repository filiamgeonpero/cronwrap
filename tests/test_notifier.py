"""Tests for cronwrap.notifier."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.notifier import (
    WebhookConfig,
    build_slack_payload,
    notify,
    send_webhook,
)


class TestBuildSlackPayload:
    def test_failure_payload_color(self):
        payload = build_slack_payload("backup", "Exit code 1", success=False)
        assert payload["attachments"][0]["color"] == "#ff0000"

    def test_success_payload_color(self):
        payload = build_slack_payload("backup", "Done", success=True)
        assert payload["attachments"][0]["color"] == "#36a64f"

    def test_payload_contains_job_name(self):
        payload = build_slack_payload("my-job", "msg", success=False)
        assert "my-job" in payload["attachments"][0]["title"]

    def test_payload_contains_message(self):
        payload = build_slack_payload("job", "some detail", success=False)
        assert payload["attachments"][0]["text"] == "some detail"

    def test_success_title_says_succeeded(self):
        payload = build_slack_payload("job", "", success=True)
        assert "succeeded" in payload["attachments"][0]["title"]

    def test_failure_title_says_failed(self):
        payload = build_slack_payload("job", "", success=False)
        assert "failed" in payload["attachments"][0]["title"]


class TestSendWebhook:
    def _make_response(self, status=200):
        mock_resp = MagicMock()
        mock_resp.getcode.return_value = status
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_returns_true_on_200(self):
        config = WebhookConfig(url="http://example.com/hook")
        payload = {"text": "hello"}
        with patch("urllib.request.urlopen", return_value=self._make_response(200)):
            result = send_webhook(config, payload)
        assert result is True

    def test_returns_false_on_non_200(self):
        config = WebhookConfig(url="http://example.com/hook")
        payload = {"text": "hello"}
        with patch("urllib.request.urlopen", return_value=self._make_response(500)):
            result = send_webhook(config, payload)
        assert result is False

    def test_returns_false_on_url_error(self):
        import urllib.error

        config = WebhookConfig(url="http://bad-host/hook")
        payload = {"text": "hello"}
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            result = send_webhook(config, payload)
        assert result is False

    def test_sends_json_body(self):
        config = WebhookConfig(url="http://example.com/hook")
        payload = {"key": "value"}
        captured = {}

        def fake_urlopen(req, timeout):
            captured["data"] = req.data
            return self._make_response(200)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            send_webhook(config, payload)

        assert json.loads(captured["data"]) == payload


class TestNotify:
    def test_returns_true_on_success(self):
        with patch("cronwrap.notifier.send_webhook", return_value=True) as mock_send:
            result = notify("http://hook", "my-job", "all good", success=True)
        assert result is True
        mock_send.assert_called_once()

    def test_passes_correct_job_name(self):
        with patch("cronwrap.notifier.send_webhook", return_value=True) as mock_send:
            notify("http://hook", "nightly-backup", "done", success=False)
        payload = mock_send.call_args[0][1]
        assert "nightly-backup" in payload["attachments"][0]["title"]
