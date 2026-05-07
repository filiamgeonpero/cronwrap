"""Tests for cronwrap.schedule_runner."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.schedule_runner import tick


def _make_job(name: str, schedule: str | None, command: str = "echo hi") -> MagicMock:
    job = MagicMock()
    job.name = name
    job.schedule = schedule
    job.command = command
    return job


class TestTick:
    def test_returns_triggered_names(self):
        job = _make_job("nightly", "0 0 * * *")
        now = datetime(2024, 1, 15, 0, 0)
        with patch("cronwrap.schedule_runner.run_job") as mock_run:
            result = tick([job], now=now)
        assert result == ["nightly"]
        mock_run.assert_called_once_with(job)

    def test_skips_non_due_job(self):
        job = _make_job("nightly", "0 0 * * *")
        now = datetime(2024, 1, 15, 12, 30)  # not midnight
        with patch("cronwrap.schedule_runner.run_job") as mock_run:
            result = tick([job], now=now)
        assert result == []
        mock_run.assert_not_called()

    def test_skips_job_without_schedule(self):
        job = _make_job("adhoc", None)
        with patch("cronwrap.schedule_runner.run_job") as mock_run:
            result = tick([job], now=datetime(2024, 1, 15, 0, 0))
        assert result == []
        mock_run.assert_not_called()

    def test_multiple_jobs_only_due_triggered(self):
        due_job = _make_job("due", "* * * * *")
        not_due_job = _make_job("not_due", "0 0 1 1 *")  # Jan 1st midnight only
        now = datetime(2024, 6, 15, 10, 5)
        with patch("cronwrap.schedule_runner.run_job"):
            result = tick([due_job, not_due_job], now=now)
        assert "due" in result
        assert "not_due" not in result

    def test_invalid_expression_logs_error_and_continues(self, caplog):
        bad_job = _make_job("broken", "99 99 * * *")
        good_job = _make_job("good", "* * * * *")
        now = datetime(2024, 1, 15, 0, 0)
        import logging
        with caplog.at_level(logging.ERROR, logger="cronwrap.schedule_runner"):
            with patch("cronwrap.schedule_runner.run_job"):
                result = tick([bad_job, good_job], now=now)
        assert "good" in result
        assert "broken" not in result
        assert any("broken" in r.message for r in caplog.records)

    def test_run_job_exception_does_not_abort_remaining(self):
        job1 = _make_job("first", "* * * * *")
        job2 = _make_job("second", "* * * * *")
        now = datetime(2024, 1, 15, 12, 0)
        call_count = 0

        def side_effect(job):
            nonlocal call_count
            call_count += 1
            if job.name == "first":
                raise RuntimeError("boom")

        with patch("cronwrap.schedule_runner.run_job", side_effect=side_effect):
            result = tick([job1, job2], now=now)

        assert call_count == 2
        assert "second" in result
