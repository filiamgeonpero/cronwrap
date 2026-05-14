"""Tests for cronwrap.dependency_hooks."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from cronwrap.dependencies import DependencyConfig
from cronwrap.dependency_hooks import gate_on_dependencies, log_dependency_skip
from cronwrap.history import ExecutionRecord


def _make_record(exit_code: int, age_seconds: float) -> ExecutionRecord:
    r = ExecutionRecord.__new__(ExecutionRecord)
    r.exit_code = exit_code
    r.finished_at = time.time() - age_seconds
    r.started_at = r.finished_at
    r.stdout = r.stderr = ""
    return r


@pytest.fixture()
def mock_history():
    return MagicMock()


class TestGateOnDependencies:
    def test_no_config_allows_run(self, mock_history):
        assert gate_on_dependencies("job", None, mock_history) is True

    def test_empty_requires_allows_run(self, mock_history):
        cfg = DependencyConfig(requires=[])
        assert gate_on_dependencies("job", cfg, mock_history) is True

    def test_satisfied_deps_allow_run(self, mock_history):
        mock_history.query.return_value = [_make_record(0, 60)]
        cfg = DependencyConfig(requires=["dep_a"], within_seconds=3600)
        assert gate_on_dependencies("myjob", cfg, mock_history) is True

    def test_unsatisfied_dep_blocks_run(self, mock_history):
        mock_history.query.return_value = []  # never ran
        cfg = DependencyConfig(requires=["dep_a"], within_seconds=3600)
        assert gate_on_dependencies("myjob", cfg, mock_history) is False

    def test_stale_dep_blocks_run(self, mock_history):
        mock_history.query.return_value = [_make_record(0, 7200)]
        cfg = DependencyConfig(requires=["dep_a"], within_seconds=3600)
        assert gate_on_dependencies("myjob", cfg, mock_history) is False

    def test_logs_warning_when_blocked(self, mock_history, caplog):
        import logging
        mock_history.query.return_value = []
        cfg = DependencyConfig(requires=["dep_x"], within_seconds=3600)
        with caplog.at_level(logging.WARNING, logger="cronwrap.dependency_hooks"):
            gate_on_dependencies("myjob", cfg, mock_history)
        assert "dep_x" in caplog.text
        assert "myjob" in caplog.text

    def test_logs_debug_when_allowed(self, mock_history, caplog):
        import logging
        mock_history.query.return_value = [_make_record(0, 10)]
        cfg = DependencyConfig(requires=["dep_ok"], within_seconds=3600)
        with caplog.at_level(logging.DEBUG, logger="cronwrap.dependency_hooks"):
            gate_on_dependencies("myjob", cfg, mock_history)
        assert "dep_ok" in caplog.text


class TestLogDependencySkip:
    def test_emits_log_with_job_name(self, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="cronwrap.dependency_hooks"):
            log_dependency_skip("batch_job", ["etl_job"])
        assert "batch_job" in caplog.text

    def test_emits_log_with_unmet_names(self, caplog):
        import logging
        with caplog.at_level(logging.INFO, logger="cronwrap.dependency_hooks"):
            log_dependency_skip("batch_job", ["etl_job", "ingest_job"])
        assert "etl_job" in caplog.text
        assert "ingest_job" in caplog.text
