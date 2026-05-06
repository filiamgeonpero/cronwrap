"""Tests for cronwrap.metrics."""
import pytest

from unittest.mock import MagicMock
from cronwrap.metrics import compute_metrics, format_metrics, JobMetrics
from cronwrap.history import ExecutionRecord


def _make_record(exit_code, duration):
    r = MagicMock(spec=ExecutionRecord)
    r.exit_code = exit_code
    r.duration_seconds = duration
    return r


@pytest.fixture
def mock_history():
    return MagicMock()


class TestComputeMetrics:
    def test_empty_history_returns_zero_totals(self, mock_history):
        mock_history.get_history.return_value = []
        m = compute_metrics("backup", mock_history)
        assert m.total_runs == 0
        assert m.successful_runs == 0
        assert m.failed_runs == 0
        assert m.success_rate == 0.0
        assert m.avg_duration_seconds is None

    def test_all_successful(self, mock_history):
        mock_history.get_history.return_value = [
            _make_record(0, 10.0),
            _make_record(0, 20.0),
        ]
        m = compute_metrics("backup", mock_history)
        assert m.total_runs == 2
        assert m.successful_runs == 2
        assert m.failed_runs == 0
        assert m.success_rate == 100.0

    def test_mixed_results(self, mock_history):
        mock_history.get_history.return_value = [
            _make_record(0, 5.0),
            _make_record(1, 3.0),
            _make_record(0, 7.0),
        ]
        m = compute_metrics("sync", mock_history)
        assert m.successful_runs == 2
        assert m.failed_runs == 1
        assert pytest.approx(m.success_rate, 0.1) == 66.7

    def test_duration_stats(self, mock_history):
        mock_history.get_history.return_value = [
            _make_record(0, 10.0),
            _make_record(0, 20.0),
            _make_record(0, 30.0),
        ]
        m = compute_metrics("job", mock_history)
        assert m.avg_duration_seconds == 20.0
        assert m.min_duration_seconds == 10.0
        assert m.max_duration_seconds == 30.0

    def test_last_exit_code_is_most_recent(self, mock_history):
        mock_history.get_history.return_value = [
            _make_record(2, 1.0),
            _make_record(0, 1.0),
        ]
        m = compute_metrics("job", mock_history)
        assert m.last_exit_code == 2

    def test_uses_limit_parameter(self, mock_history):
        mock_history.get_history.return_value = []
        compute_metrics("job", mock_history, limit=50)
        mock_history.get_history.assert_called_once_with("job", limit=50)


class TestFormatMetrics:
    def test_contains_job_name(self):
        m = JobMetrics("nightly", 5, 4, 1, 80.0, 12.5, 10.0, 15.0, 0)
        output = format_metrics(m)
        assert "nightly" in output

    def test_contains_success_rate(self):
        m = JobMetrics("nightly", 5, 4, 1, 80.0, 12.5, 10.0, 15.0, 0)
        output = format_metrics(m)
        assert "80.0%" in output

    def test_no_duration_when_none(self):
        m = JobMetrics("empty", 0, 0, 0, 0.0, None, None, None, None)
        output = format_metrics(m)
        assert "duration" not in output.lower()
