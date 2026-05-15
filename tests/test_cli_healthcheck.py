"""Tests for cronwrap.cli_healthcheck."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.cli_healthcheck import build_parser, main
from cronwrap.healthcheck import HealthStatus


@pytest.fixture
def parser():
    return build_parser()


class TestBuildParser:
    def test_jobs_required(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_single_job(self, parser):
        args = parser.parse_args(["myjob"])
        assert args.jobs == ["myjob"]

    def test_multiple_jobs(self, parser):
        args = parser.parse_args(["job-a", "job-b"])
        assert args.jobs == ["job-a", "job-b"]

    def test_default_db(self, parser):
        args = parser.parse_args(["myjob"])
        assert args.db == "cronwrap_history.db"

    def test_custom_db(self, parser):
        args = parser.parse_args(["myjob", "--db", "/tmp/test.db"])
        assert args.db == "/tmp/test.db"

    def test_default_max_age(self, parser):
        args = parser.parse_args(["myjob"])
        assert args.max_age == 0

    def test_custom_max_age(self, parser):
        args = parser.parse_args(["myjob", "--max-age", "3600"])
        assert args.max_age == 3600.0

    def test_fail_fast_default_false(self, parser):
        args = parser.parse_args(["myjob"])
        assert args.fail_fast is False

    def test_fail_fast_flag(self, parser):
        args = parser.parse_args(["myjob", "--fail-fast"])
        assert args.fail_fast is True


class TestMain:
    def _healthy_status(self, name="myjob"):
        return HealthStatus(name, True, time.time(), 0, "ok")

    def _unhealthy_status(self, name="myjob"):
        return HealthStatus(name, False, None, 1, "no history")

    @patch("cronwrap.cli_healthcheck.JobHistory")
    @patch("cronwrap.cli_healthcheck.check_health")
    def test_exits_zero_when_all_healthy(self, mock_check, mock_history_cls, capsys):
        mock_check.return_value = self._healthy_status()
        main(["myjob"])
        # no SystemExit raised means exit code 0

    @patch("cronwrap.cli_healthcheck.JobHistory")
    @patch("cronwrap.cli_healthcheck.check_health")
    def test_exits_one_when_unhealthy(self, mock_check, mock_history_cls):
        mock_check.return_value = self._unhealthy_status()
        with pytest.raises(SystemExit) as exc_info:
            main(["myjob"])
        assert exc_info.value.code == 1

    @patch("cronwrap.cli_healthcheck.JobHistory")
    @patch("cronwrap.cli_healthcheck.check_health")
    def test_output_contains_job_name(self, mock_check, mock_history_cls, capsys):
        mock_check.return_value = self._healthy_status("special-job")
        main(["special-job"])
        captured = capsys.readouterr()
        assert "special-job" in captured.out
