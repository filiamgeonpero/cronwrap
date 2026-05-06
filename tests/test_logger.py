"""Tests for cronwrap.logger module."""

import logging
import os
import tempfile
from pathlib import Path

import pytest

from cronwrap.logger import log_execution, setup_logger


@pytest.fixture()
def tmp_log_dir(tmp_path: Path) -> str:
    return str(tmp_path / "logs")


class TestSetupLogger:
    def test_returns_logger_instance(self, tmp_log_dir):
        logger = setup_logger("test_job", log_dir=tmp_log_dir)
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_job"

    def test_creates_log_directory(self, tmp_log_dir):
        setup_logger("test_job", log_dir=tmp_log_dir)
        assert Path(tmp_log_dir).is_dir()

    def test_creates_log_file(self, tmp_log_dir):
        setup_logger("my_cron", log_dir=tmp_log_dir)
        log_file = Path(tmp_log_dir) / "my_cron.log"
        assert log_file.exists()

    def test_has_two_handlers(self, tmp_log_dir):
        logger = setup_logger("test_job", log_dir=tmp_log_dir)
        assert len(logger.handlers) == 2

    def test_calling_twice_does_not_duplicate_handlers(self, tmp_log_dir):
        setup_logger("test_job", log_dir=tmp_log_dir)
        logger = setup_logger("test_job", log_dir=tmp_log_dir)
        assert len(logger.handlers) == 2


class TestLogExecution:
    def test_success_logged_at_info(self, tmp_log_dir, caplog):
        logger = setup_logger("ok_job", log_dir=tmp_log_dir)
        with caplog.at_level(logging.INFO, logger="ok_job"):
            log_execution(logger, "ok_job", exit_code=0,
                          stdout="done", stderr="", duration_seconds=1.23)
        assert "SUCCESS" in caplog.text
        assert "exit_code=0" in caplog.text

    def test_failure_logged_at_info(self, tmp_log_dir, caplog):
        logger = setup_logger("fail_job", log_dir=tmp_log_dir)
        with caplog.at_level(logging.INFO, logger="fail_job"):
            log_execution(logger, "fail_job", exit_code=1,
                          stdout="", stderr="error!", duration_seconds=0.5)
        assert "FAILURE" in caplog.text

    def test_stderr_logged_as_warning(self, tmp_log_dir, caplog):
        logger = setup_logger("warn_job", log_dir=tmp_log_dir)
        with caplog.at_level(logging.WARNING, logger="warn_job"):
            log_execution(logger, "warn_job", exit_code=0,
                          stdout="", stderr="something went wrong", duration_seconds=2.0)
        assert "something went wrong" in caplog.text

    def test_duration_in_log_message(self, tmp_log_dir, caplog):
        logger = setup_logger("timed_job", log_dir=tmp_log_dir)
        with caplog.at_level(logging.INFO, logger="timed_job"):
            log_execution(logger, "timed_job", exit_code=0,
                          stdout="", stderr="", duration_seconds=42.7)
        assert "42.70" in caplog.text
