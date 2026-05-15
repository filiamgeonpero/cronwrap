"""Tests for cronwrap.ratelimit."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from cronwrap.ratelimit import (
    RateLimitConfig,
    is_rate_limited,
    runs_in_window,
    runs_remaining,
)


def _ts(offset: float = 0.0) -> float:
    """Return a UTC timestamp *offset* seconds from now."""
    return datetime.now(tz=timezone.utc).timestamp() + offset


def _make_record(finished_at: float | None):
    rec = MagicMock()
    rec.finished_at = finished_at
    return rec


@pytest.fixture()
def mock_history():
    return MagicMock()


class TestRateLimitConfig:
    def test_defaults(self):
        cfg = RateLimitConfig()
        assert cfg.max_runs == 0
        assert cfg.window_seconds == 3600

    def test_enabled_false_when_zero_max(self):
        assert not RateLimitConfig(max_runs=0).enabled

    def test_enabled_false_when_zero_window(self):
        assert not RateLimitConfig(max_runs=5, window_seconds=0).enabled

    def test_enabled_true_when_positive(self):
        assert RateLimitConfig(max_runs=3, window_seconds=60).enabled


class TestRunsInWindow:
    def test_empty_history_returns_zero(self, mock_history):
        mock_history.query.return_value = []
        assert runs_in_window(mock_history, "job", 3600) == 0

    def test_counts_recent_runs(self, mock_history):
        mock_history.query.return_value = [
            _make_record(_ts(-10)),
            _make_record(_ts(-20)),
        ]
        assert runs_in_window(mock_history, "job", 3600) == 2

    def test_excludes_old_runs(self, mock_history):
        mock_history.query.return_value = [
            _make_record(_ts(-7200)),  # outside 1-hour window
            _make_record(_ts(-10)),
        ]
        assert runs_in_window(mock_history, "job", 3600) == 1

    def test_ignores_unfinished_runs(self, mock_history):
        mock_history.query.return_value = [
            _make_record(None),
            _make_record(_ts(-5)),
        ]
        assert runs_in_window(mock_history, "job", 3600) == 1


class TestIsRateLimited:
    def test_disabled_config_never_limits(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-1))] * 100
        assert not is_rate_limited(mock_history, "job", RateLimitConfig(max_runs=0))

    def test_not_limited_when_under_max(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))]
        cfg = RateLimitConfig(max_runs=3, window_seconds=3600)
        assert not is_rate_limited(mock_history, "job", cfg)

    def test_limited_when_at_max(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))] * 3
        cfg = RateLimitConfig(max_runs=3, window_seconds=3600)
        assert is_rate_limited(mock_history, "job", cfg)


class TestRunsRemaining:
    def test_returns_none_when_disabled(self, mock_history):
        assert runs_remaining(mock_history, "job", RateLimitConfig()) is None

    def test_returns_correct_remaining(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))] * 2
        cfg = RateLimitConfig(max_runs=5, window_seconds=3600)
        assert runs_remaining(mock_history, "job", cfg) == 3

    def test_returns_zero_when_exhausted(self, mock_history):
        mock_history.query.return_value = [_make_record(_ts(-5))] * 5
        cfg = RateLimitConfig(max_runs=5, window_seconds=3600)
        assert runs_remaining(mock_history, "job", cfg) == 0
