"""Tests for cronwrap.dependencies."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from cronwrap.dependencies import (
    DependencyConfig,
    all_dependencies_met,
    check_dependency,
    dependencies_met,
    last_success_age,
    unmet_dependencies,
)
from cronwrap.history import ExecutionRecord


def _make_record(exit_code: int, finished_at: float | None) -> ExecutionRecord:
    r = ExecutionRecord.__new__(ExecutionRecord)
    r.job_name = "dep_job"
    r.exit_code = exit_code
    r.finished_at = finished_at
    r.started_at = finished_at or time.time()
    r.stdout = ""
    r.stderr = ""
    return r


@pytest.fixture()
def mock_history():
    return MagicMock()


class TestLastSuccessAge:
    def test_returns_none_when_no_records(self, mock_history):
        mock_history.query.return_value = []
        assert last_success_age("job", mock_history) is None

    def test_returns_none_when_only_failures(self, mock_history):
        mock_history.query.return_value = [_make_record(1, time.time() - 100)]
        assert last_success_age("job", mock_history) is None

    def test_returns_age_of_last_success(self, mock_history):
        finished = time.time() - 300
        mock_history.query.return_value = [_make_record(0, finished)]
        age = last_success_age("job", mock_history)
        assert age is not None
        assert 299 < age < 302

    def test_skips_failed_records_before_success(self, mock_history):
        now = time.time()
        mock_history.query.return_value = [
            _make_record(1, now - 10),
            _make_record(0, now - 500),
        ]
        age = last_success_age("job", mock_history)
        assert age is not None
        assert age > 490


class TestCheckDependency:
    def test_returns_true_when_within_window(self, mock_history):
        mock_history.query.return_value = [_make_record(0, time.time() - 60)]
        assert check_dependency("dep", 3600, mock_history) is True

    def test_returns_false_when_outside_window(self, mock_history):
        mock_history.query.return_value = [_make_record(0, time.time() - 7200)]
        assert check_dependency("dep", 3600, mock_history) is False

    def test_returns_false_when_never_ran(self, mock_history):
        mock_history.query.return_value = []
        assert check_dependency("dep", 3600, mock_history) is False


class TestDependenciesMet:
    def test_empty_requires_returns_empty_dict(self, mock_history):
        cfg = DependencyConfig(requires=[])
        assert dependencies_met(cfg, mock_history) == {}

    def test_returns_mapping_for_each_dep(self, mock_history):
        mock_history.query.return_value = [_make_record(0, time.time() - 10)]
        cfg = DependencyConfig(requires=["a", "b"], within_seconds=3600)
        result = dependencies_met(cfg, mock_history)
        assert set(result.keys()) == {"a", "b"}

    def test_all_met(self, mock_history):
        mock_history.query.return_value = [_make_record(0, time.time() - 10)]
        cfg = DependencyConfig(requires=["a"], within_seconds=3600)
        assert all_dependencies_met(cfg, mock_history) is True

    def test_not_all_met(self, mock_history):
        mock_history.query.return_value = []
        cfg = DependencyConfig(requires=["a"], within_seconds=3600)
        assert all_dependencies_met(cfg, mock_history) is False

    def test_unmet_returns_names(self, mock_history):
        mock_history.query.return_value = []
        cfg = DependencyConfig(requires=["x", "y"], within_seconds=3600)
        unmet = unmet_dependencies(cfg, mock_history)
        assert "x" in unmet
        assert "y" in unmet

    def test_no_requires_all_met(self, mock_history):
        cfg = DependencyConfig(requires=[])
        assert all_dependencies_met(cfg, mock_history) is True
