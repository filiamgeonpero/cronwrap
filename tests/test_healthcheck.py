"""Tests for cronwrap.healthcheck."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwrap.healthcheck import HealthStatus, check_health, render_health
from cronwrap.history import ExecutionRecord


def _make_record(
    job_name: str = "myjob",
    exit_code: int = 0,
    finished_at: float | None = None,
) -> ExecutionRecord:
    finished_at = finished_at if finished_at is not None else time.time()
    return ExecutionRecord(
        id=1,
        job_name=job_name,
        started_at=finished_at - 1.0,
        finished_at=finished_at,
        exit_code=exit_code,
        stdout="",
        stderr="",
    )


@pytest.fixture
def mock_history():
    return MagicMock()


class TestCheckHealth:
    def test_no_history_returns_unhealthy(self, mock_history):
        mock_history.query.return_value = []
        status = check_health("myjob", mock_history)
        assert status.healthy is False
        assert "no execution history" in status.message

    def test_only_failures_returns_unhealthy(self, mock_history):
        records = [_make_record(exit_code=1)]
        mock_history.query.return_value = records
        status = check_health("myjob", mock_history)
        assert status.healthy is False
        assert "no successful run" in status.message

    def test_recent_success_returns_healthy(self, mock_history):
        records = [_make_record(exit_code=0)]
        mock_history.query.return_value = records
        status = check_health("myjob", mock_history)
        assert status.healthy is True
        assert status.message == "ok"

    def test_stale_success_returns_unhealthy(self, mock_history):
        old_ts = time.time() - 7200  # 2 hours ago
        records = [_make_record(exit_code=0, finished_at=old_ts)]
        mock_history.query.return_value = records
        status = check_health("myjob", mock_history, max_age_seconds=3600)
        assert status.healthy is False
        assert "ago" in status.message

    def test_fresh_success_within_max_age_is_healthy(self, mock_history):
        recent_ts = time.time() - 60
        records = [_make_record(exit_code=0, finished_at=recent_ts)]
        mock_history.query.return_value = records
        status = check_health("myjob", mock_history, max_age_seconds=3600)
        assert status.healthy is True

    def test_last_success_ts_populated(self, mock_history):
        ts = time.time() - 10
        records = [_make_record(exit_code=0, finished_at=ts)]
        mock_history.query.return_value = records
        status = check_health("myjob", mock_history)
        assert status.last_success_ts == pytest.approx(ts, abs=1)

    def test_job_name_preserved(self, mock_history):
        mock_history.query.return_value = []
        status = check_health("special-job", mock_history)
        assert status.job_name == "special-job"


class TestRenderHealth:
    def test_contains_job_name(self):
        s = HealthStatus("myjob", True, None, 0, "ok")
        output = render_health([s])
        assert "myjob" in output

    def test_ok_status_label(self):
        s = HealthStatus("myjob", True, None, 0, "ok")
        output = render_health([s])
        assert "OK" in output

    def test_fail_status_label(self):
        s = HealthStatus("myjob", False, None, 1, "no history")
        output = render_health([s])
        assert "FAIL" in output

    def test_multiple_jobs_all_present(self):
        statuses = [
            HealthStatus("job-a", True, None, 0, "ok"),
            HealthStatus("job-b", False, None, 1, "stale"),
        ]
        output = render_health(statuses)
        assert "job-a" in output
        assert "job-b" in output
