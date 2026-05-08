"""Tests for cronwrap.dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.dashboard import JobStatus, collect_status, render_dashboard
from cronwrap.history import ExecutionRecord


def _make_record(
    job_name: str = "backup",
    exit_code: int = 0,
    duration: float = 5.0,
    started_at: str = "2024-01-15T10:00:00",
) -> ExecutionRecord:
    return ExecutionRecord(
        id=1,
        job_name=job_name,
        started_at=started_at,
        finished_at="2024-01-15T10:00:05",
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration_s=duration,
    )


@pytest.fixture()
 def mock_history():
    h = MagicMock()
    h.get_history.return_value = [_make_record()]
    return h


class TestCollectStatus:
    def test_returns_one_status_per_job(self, mock_history):
        statuses = collect_status(mock_history, ["backup", "cleanup"])
        assert len(statuses) == 2

    def test_status_name_matches_job(self, mock_history):
        statuses = collect_status(mock_history, ["backup"])
        assert statuses[0].name == "backup"

    def test_state_ok_on_zero_exit(self, mock_history):
        statuses = collect_status(mock_history, ["backup"])
        assert statuses[0].state == "OK"

    def test_state_failed_on_nonzero_exit(self, mock_history):
        mock_history.get_history.return_value = [_make_record(exit_code=1)]
        statuses = collect_status(mock_history, ["backup"])
        assert statuses[0].state == "FAILED"

    def test_never_run_when_no_records(self, mock_history):
        mock_history.get_history.return_value = []
        statuses = collect_status(mock_history, ["backup"])
        assert statuses[0].state == "NEVER RUN"
        assert statuses[0].last_run is None


class TestRenderDashboard:
    def _status(self, name="backup", exit_code=0):
        return JobStatus(
            name=name,
            last_run=datetime(2024, 1, 15, 10, 0, 0),
            last_exit_code=exit_code,
            total_runs=10,
            success_rate=0.9,
            avg_duration_s=3.5,
        )

    def test_empty_returns_message(self):
        assert "No jobs" in render_dashboard([])

    def test_contains_job_name(self):
        output = render_dashboard([self._status()])
        assert "backup" in output

    def test_contains_ok_state(self):
        output = render_dashboard([self._status()])
        assert "OK" in output

    def test_contains_failed_state(self):
        output = render_dashboard([self._status(exit_code=1)])
        assert "FAILED" in output

    def test_contains_header(self):
        output = render_dashboard([self._status()])
        assert "JOB" in output and "STATE" in output

    def test_multiple_jobs_all_present(self):
        statuses = [self._status("job_a"), self._status("job_b")]
        output = render_dashboard(statuses)
        assert "job_a" in output and "job_b" in output
