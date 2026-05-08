"""Tests for cronwrap.cli_dashboard."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cronwrap.cli_dashboard import build_dashboard_parser, main


@pytest.fixture()
def parser():
    return build_dashboard_parser()


class TestBuildDashboardParser:
    def test_jobs_required(self, parser):
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_single_job(self, parser):
        args = parser.parse_args(["backup"])
        assert args.jobs == ["backup"]

    def test_multiple_jobs(self, parser):
        args = parser.parse_args(["backup", "cleanup"])
        assert args.jobs == ["backup", "cleanup"]

    def test_default_db(self, parser):
        args = parser.parse_args(["backup"])
        assert args.db == "cronwrap_history.db"

    def test_custom_db(self, parser):
        args = parser.parse_args(["backup", "--db", "/tmp/test.db"])
        assert args.db == "/tmp/test.db"

    def test_default_output_format(self, parser):
        args = parser.parse_args(["backup"])
        assert args.output == "text"


class TestMain:
    def test_returns_zero_on_success(self, capsys):
        with patch("cronwrap.cli_dashboard.JobHistory") as MockHistory, \
             patch("cronwrap.cli_dashboard.collect_status") as mock_collect, \
             patch("cronwrap.cli_dashboard.render_dashboard", return_value="OK\n") as mock_render:
            mock_collect.return_value = []
            result = main(["backup"])
        assert result == 0

    def test_output_written_to_stdout(self, capsys):
        with patch("cronwrap.cli_dashboard.JobHistory"), \
             patch("cronwrap.cli_dashboard.collect_status", return_value=[]), \
             patch("cronwrap.cli_dashboard.render_dashboard", return_value="DASHBOARD\n"):
            main(["backup"])
        captured = capsys.readouterr()
        assert "DASHBOARD" in captured.out

    def test_passes_jobs_to_collect(self):
        with patch("cronwrap.cli_dashboard.JobHistory"), \
             patch("cronwrap.cli_dashboard.collect_status", return_value=[]) as mock_collect, \
             patch("cronwrap.cli_dashboard.render_dashboard", return_value=""):
            main(["job_a", "job_b"])
        _, called_jobs = mock_collect.call_args[0]
        assert called_jobs == ["job_a", "job_b"]
