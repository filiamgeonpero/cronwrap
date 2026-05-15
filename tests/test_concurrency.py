"""Tests for cronwrap.concurrency."""

from __future__ import annotations

import os
import pytest

from cronwrap.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimitError,
    active_count,
    check_concurrency,
    deregister_run,
    register_run,
)


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "concurrency.db")


@pytest.fixture()
def cfg(db_path):
    return ConcurrencyConfig(max_instances=2, db_path=db_path)


class TestConcurrencyConfig:
    def test_defaults(self):
        c = ConcurrencyConfig()
        assert c.max_instances == 1
        assert c.enabled is True

    def test_enabled_false_when_zero(self):
        c = ConcurrencyConfig(max_instances=0)
        assert c.enabled is False

    def test_custom_values(self):
        c = ConcurrencyConfig(max_instances=5, db_path="/tmp/x.db")
        assert c.max_instances == 5
        assert c.db_path == "/tmp/x.db"


class TestActiveCount:
    def test_zero_when_no_runs(self, cfg, db_path):
        assert active_count("backup", db_path) == 0

    def test_increments_on_register(self, cfg, db_path):
        register_run("backup", os.getpid(), db_path)
        assert active_count("backup", db_path) == 1

    def test_decrements_on_deregister(self, cfg, db_path):
        run_id = register_run("backup", os.getpid(), db_path)
        deregister_run(run_id, db_path)
        assert active_count("backup", db_path) == 0

    def test_isolates_job_names(self, cfg, db_path):
        register_run("job_a", os.getpid(), db_path)
        assert active_count("job_b", db_path) == 0


class TestRegisterRun:
    def test_returns_positive_int(self, db_path):
        run_id = register_run("myjob", 1234, db_path)
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_multiple_registrations(self, db_path):
        id1 = register_run("myjob", 1, db_path)
        id2 = register_run("myjob", 2, db_path)
        assert id1 != id2
        assert active_count("myjob", db_path) == 2


class TestCheckConcurrency:
    def test_allows_when_under_limit(self, cfg, db_path):
        register_run("job", os.getpid(), db_path)
        # limit is 2, only 1 active — should not raise
        check_concurrency("job", cfg)

    def test_raises_when_at_limit(self, cfg, db_path):
        register_run("job", 1, db_path)
        register_run("job", 2, db_path)
        with pytest.raises(ConcurrencyLimitError):
            check_concurrency("job", cfg)

    def test_no_check_when_disabled(self, db_path):
        cfg = ConcurrencyConfig(max_instances=0, db_path=db_path)
        # Fill beyond a real limit to prove disabled means no raise
        for _ in range(10):
            register_run("job", os.getpid(), db_path)
        check_concurrency("job", cfg)  # should not raise
