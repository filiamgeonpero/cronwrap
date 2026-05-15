"""Tests for cronwrap.ratelimit_hooks."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.ratelimit import RateLimitConfig
from cronwrap.ratelimit_hooks import gate_on_rate_limit, log_rate_limit_skip


def _ts(offset: float = 0.0) -> float:
    return datetime.now(tz=timezone.utc).timestamp() + offset


def _make_record(finished_at):
    rec = MagicMock()
    rec.finished_at = finished_at
    return rec


@pytest.fixture()
def mock_history():
    return MagicMock()


class TestGateOnRateLimit:
    def test_no_config_allows_run(self, mock_history):
        assert gate_on_rate_limit(mock_history, "job", None) is True

    def test_disabled_config_allows_run(self, mock_history):
        cfg = RateLimitConfig(max_runs=0)
        assert gate_on_rate_limit(mock_history, "job", cfg) is True

    def test_allows_run_when_under_limit(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))]
        cfg = RateLimitConfig(max_runs=3, window_seconds=3600)
        assert gate_on_rate_limit(mock_history, "job", cfg) is True

    def test_blocks_run_when_at_limit(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))] * 3
        cfg = RateLimitConfig(max_runs=3, window_seconds=3600)
        assert gate_on_rate_limit(mock_history, "job", cfg) is False

    def test_logs_warning_when_blocked(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))] * 5
        cfg = RateLimitConfig(max_runs=5, window_seconds=60)
        with patch("cronwrap.ratelimit_hooks.logger") as mock_log:
            gate_on_rate_limit(mock_history, "myjob", cfg)
            mock_log.warning.assert_called_once()
            args = mock_log.warning.call_args[0]
            assert "myjob" in args[1]

    def test_logs_debug_when_allowed(self, mock_history):
        mock_history.query.return_value = []
        cfg = RateLimitConfig(max_runs=5, window_seconds=3600)
        with patch("cronwrap.ratelimit_hooks.logger") as mock_log:
            gate_on_rate_limit(mock_history, "myjob", cfg)
            mock_log.debug.assert_called_once()


class TestLogRateLimitSkip:
    def test_emits_info_log(self):
        cfg = RateLimitConfig(max_runs=2, window_seconds=300)
        with patch("cronwrap.ratelimit_hooks.logger") as mock_log:
            log_rate_limit_skip("backup-job", cfg)
            mock_log.info.assert_called_once()
            message = mock_log.info.call_args[0][0]
            assert "skipping" in message

    def test_log_contains_job_name(self):
        cfg = RateLimitConfig(max_runs=1, window_seconds=60)
        with patch("cronwrap.ratelimit_hooks.logger") as mock_log:
            log_rate_limit_skip("my-job", cfg)
            args = mock_log.info.call_args[0]
            assert "my-job" in args[1]
