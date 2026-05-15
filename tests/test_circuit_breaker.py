"""Tests for cronwrap.circuit_breaker and cronwrap.circuit_breaker_hooks."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwrap.circuit_breaker import (
    CircuitBreakerConfig,
    consecutive_failures,
    is_open,
    last_failure_age,
    seconds_until_recovery,
)
from cronwrap.circuit_breaker_hooks import gate_on_circuit_breaker, log_circuit_breaker_skip


def _make_record(exit_code: int, finished_at: float | None = None):
    r = MagicMock()
    r.exit_code = exit_code
    r.finished_at = finished_at if finished_at is not None else time.time()
    return r


@pytest.fixture()
def mock_history():
    return MagicMock()


class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.enabled is False
        assert cfg.failure_threshold == 3
        assert cfg.recovery_timeout == 300

    def test_is_enabled_false_when_disabled(self):
        cfg = CircuitBreakerConfig(enabled=False, failure_threshold=3)
        assert cfg.is_enabled is False

    def test_is_enabled_false_when_threshold_zero(self):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=0)
        assert cfg.is_enabled is False

    def test_is_enabled_true(self):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=2)
        assert cfg.is_enabled is True


class TestConsecutiveFailures:
    def test_all_success_returns_zero(self, mock_history):
        mock_history.recent.return_value = [_make_record(0), _make_record(0)]
        assert consecutive_failures("job", mock_history) == 0

    def test_counts_tail_failures(self, mock_history):
        mock_history.recent.return_value = [
            _make_record(0), _make_record(1), _make_record(1)
        ]
        assert consecutive_failures("job", mock_history) == 2

    def test_stops_at_success(self, mock_history):
        mock_history.recent.return_value = [
            _make_record(1), _make_record(0), _make_record(1)
        ]
        assert consecutive_failures("job", mock_history) == 1

    def test_empty_history(self, mock_history):
        mock_history.recent.return_value = []
        assert consecutive_failures("job", mock_history) == 0


class TestIsOpen:
    def test_disabled_config_never_opens(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=False)
        mock_history.recent.return_value = [_make_record(1)] * 10
        assert is_open("job", cfg, mock_history) is False

    def test_below_threshold_not_open(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=3)
        mock_history.recent.return_value = [_make_record(1), _make_record(1)]
        assert is_open("job", cfg, mock_history) is False

    def test_open_when_threshold_reached_within_timeout(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=2, recovery_timeout=300)
        recent = time.time() - 10
        mock_history.recent.return_value = [
            _make_record(1, finished_at=recent),
            _make_record(1, finished_at=recent),
        ]
        assert is_open("job", cfg, mock_history) is True

    def test_not_open_after_recovery_timeout(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=2, recovery_timeout=60)
        old = time.time() - 120
        mock_history.recent.return_value = [
            _make_record(1, finished_at=old),
            _make_record(1, finished_at=old),
        ]
        assert is_open("job", cfg, mock_history) is False


class TestGateOnCircuitBreaker:
    def test_no_config_allows_run(self, mock_history):
        assert gate_on_circuit_breaker("job", None, mock_history) is None

    def test_disabled_config_allows_run(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=False)
        mock_history.recent.return_value = []
        assert gate_on_circuit_breaker("job", cfg, mock_history) is None

    def test_open_circuit_returns_reason_string(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=2, recovery_timeout=300)
        recent = time.time() - 5
        mock_history.recent.return_value = [
            _make_record(1, finished_at=recent),
            _make_record(1, finished_at=recent),
        ]
        reason = gate_on_circuit_breaker("myjob", cfg, mock_history)
        assert reason is not None
        assert "myjob" in reason
        assert "circuit breaker" in reason

    def test_closed_circuit_returns_none(self, mock_history):
        cfg = CircuitBreakerConfig(enabled=True, failure_threshold=3, recovery_timeout=300)
        mock_history.recent.return_value = [_make_record(0)]
        assert gate_on_circuit_breaker("job", cfg, mock_history) is None

    def test_log_skip_emits_warning(self, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="cronwrap.circuit_breaker_hooks"):
            log_circuit_breaker_skip("testjob", "3 consecutive failures")
        assert "testjob" in caplog.text
        assert "circuit_breaker" in caplog.text
