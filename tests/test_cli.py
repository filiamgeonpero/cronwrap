"""Tests for cronwrap.cli module."""

import pytest
from unittest.mock import patch, MagicMock
from cronwrap.cli import build_parser, cmd_history, cmd_last_success
from cronwrap.history import ExecutionRecord


@pytest.fixture
def parser():
    return build_parser()


SAMPLE_RECORD = ExecutionRecord(
    id=1,
    job_name="backup",
    command="tar -czf /tmp/b.tar.gz /data",
    started_at="2024-01-15T10:00:00",
    finished_at="2024-01-15T10:00:02",
    exit_code=0,
    success=True,
    duration_seconds=2.0,
)

FAIL_RECORD = ExecutionRecord(
    id=2,
    job_name="backup",
    command="tar -czf /tmp/b.tar.gz /data",
    started_at="2024-01-15T09:00:00",
    finished_at="2024-01-15T09:00:01",
    exit_code=1,
    success=False,
    duration_seconds=1.0,
    stderr_snippet="Permission denied",
)


class TestBuildParser:
    def test_history_subcommand(self, parser):
        args = parser.parse_args(["history", "my-job"])
        assert args.command == "history"
        assert args.job_name == "my-job"
        assert args.limit == 10

    def test_history_custom_limit(self, parser):
        args = parser.parse_args(["history", "my-job", "-n", "5"])
        assert args.limit == 5

    def test_last_success_subcommand(self, parser):
        args = parser.parse_args(["last-success", "my-job"])
        assert args.command == "last-success"
        assert args.job_name == "my-job"

    def test_custom_db_path(self, parser):
        args = parser.parse_args(["--db", "/tmp/test.db", "history", "job"])
        assert args.db == "/tmp/test.db"


class TestCmdHistory:
    def test_prints_records(self, capsys, tmp_path):
        db = str(tmp_path / "h.db")
        args = MagicMock(job_name="backup", limit=10, db=db)
        with patch("cronwrap.cli.JobHistory") as MockHistory:
            MockHistory.return_value.get_recent.return_value = [SAMPLE_RECORD]
            cmd_history(args)
        out = capsys.readouterr().out
        assert "backup" in out
        assert "OK" in out

    def test_no_records_message(self, capsys, tmp_path):
        db = str(tmp_path / "h.db")
        args = MagicMock(job_name="ghost", limit=10, db=db)
        with patch("cronwrap.cli.JobHistory") as MockHistory:
            MockHistory.return_value.get_recent.return_value = []
            cmd_history(args)
        out = capsys.readouterr().out
        assert "No history" in out


class TestCmdLastSuccess:
    def test_prints_last_success(self, capsys, tmp_path):
        db = str(tmp_path / "h.db")
        args = MagicMock(job_name="backup", db=db)
        with patch("cronwrap.cli.JobHistory") as MockHistory:
            MockHistory.return_value.last_success.return_value = SAMPLE_RECORD
            cmd_last_success(args)
        out = capsys.readouterr().out
        assert "OK" in out

    def test_exits_1_when_no_success(self, tmp_path):
        db = str(tmp_path / "h.db")
        args = MagicMock(job_name="never-ok", db=db)
        with patch("cronwrap.cli.JobHistory") as MockHistory:
            MockHistory.return_value.last_success.return_value = None
            with pytest.raises(SystemExit) as exc_info:
                cmd_last_success(args)
            assert exc_info.value.code == 1
