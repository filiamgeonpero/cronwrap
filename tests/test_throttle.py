"""Tests for cronwrap.throttle."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.throttle import (
    ThrottleConfig,
    is_throttled,
    last_run_seconds_ago,
    seconds_until_allowed,
)


def _make_record(started_at: float):
    rec = MagicMock()
    rec.started_at = started_at
    return rec


@pytest.fixture()
def mock_history():
    return MagicMock()


class TestThrottleConfig:
    def test_defaults(self):
        cfg = ThrottleConfig()
        assert cfg.min_interval_seconds == 0
        assert cfg.enabled is True

    def test_custom_values(self):
        cfg = ThrottleConfig(min_interval_seconds=300, enabled=False)
        assert cfg.min_interval_seconds == 300
        assert cfg.enabled is False


class TestLastRunSecondsAgo:
    def test_returns_none_when_no_history(self, mock_history):
        mock_history.get_recent.return_value = []
        result = last_run_seconds_ago("myjob", mock_history)
        assert result is None

    def test_returns_elapsed_time(self, mock_history):
        started = time.time() - 120
        mock_history.get_recent.return_value = [_make_record(started)]
        result = last_run_seconds_ago("myjob", mock_history)
        assert result == pytest.approx(120, abs=1)


class TestIsThrottled:
    def test_not_throttled_when_disabled(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=300, enabled=False)
        mock_history.get_recent.return_value = [_make_record(time.time() - 10)]
        assert is_throttled("job", cfg, mock_history) is False

    def test_not_throttled_when_interval_zero(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=0)
        mock_history.get_recent.return_value = [_make_record(time.time() - 10)]
        assert is_throttled("job", cfg, mock_history) is False

    def test_not_throttled_when_never_run(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=300)
        mock_history.get_recent.return_value = []
        assert is_throttled("job", cfg, mock_history) is False

    def test_throttled_when_too_recent(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=300)
        mock_history.get_recent.return_value = [_make_record(time.time() - 60)]
        assert is_throttled("job", cfg, mock_history) is True

    def test_not_throttled_after_interval_elapsed(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=300)
        mock_history.get_recent.return_value = [_make_record(time.time() - 400)]
        assert is_throttled("job", cfg, mock_history) is False


class TestSecondsUntilAllowed:
    def test_returns_zero_when_not_throttled(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=300)
        mock_history.get_recent.return_value = [_make_record(time.time() - 400)]
        assert seconds_until_allowed("job", cfg, mock_history) == 0.0

    def test_returns_remaining_seconds(self, mock_history):
        cfg = ThrottleConfig(min_interval_seconds=300)
        mock_history.get_recent.return_value = [_make_record(time.time() - 100)]
        remaining = seconds_until_allowed("job", cfg, mock_history)
        assert remaining == pytest.approx(200, abs=1)
