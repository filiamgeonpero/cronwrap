"""Tests for cronwrap.concurrency_hooks."""

from __future__ import annotations

import os
import pytest

from cronwrap.concurrency import (
    ConcurrencyConfig,
    ConcurrencyLimitError,
    active_count,
    register_run,
)
from cronwrap.concurrency_hooks import (
    gate_on_concurrency,
    log_concurrency_skip,
    release_concurrency_slot,
)


@pytest.fixture()
def db_path(tmp_path):
    return str(tmp_path / "hooks_concurrency.db")


@pytest.fixture()
def cfg(db_path):
    return ConcurrencyConfig(max_instances=1, db_path=db_path)


class TestGateOnConcurrency:
    def test_returns_none_when_no_config(self):
        result = gate_on_concurrency("job", None)
        assert result is None

    def test_returns_none_when_disabled(self, db_path):
        cfg = ConcurrencyConfig(max_instances=0, db_path=db_path)
        result = gate_on_concurrency("job", cfg)
        assert result is None

    def test_returns_run_id_on_success(self, cfg):
        run_id = gate_on_concurrency("job", cfg)
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_registers_active_run(self, cfg):
        gate_on_concurrency("job", cfg)
        assert active_count("job", cfg.db_path) == 1

    def test_raises_when_limit_reached(self, cfg):
        register_run("job", os.getpid(), cfg.db_path)  # fills the single slot
        with pytest.raises(ConcurrencyLimitError):
            gate_on_concurrency("job", cfg)


class TestReleaseConcurrencySlot:
    def test_noop_when_run_id_none(self, cfg):
        # Should not raise
        release_concurrency_slot("job", None, cfg)

    def test_noop_when_cfg_none(self):
        release_concurrency_slot("job", 42, None)

    def test_releases_slot(self, cfg):
        run_id = gate_on_concurrency("job", cfg)
        assert active_count("job", cfg.db_path) == 1
        release_concurrency_slot("job", run_id, cfg)
        assert active_count("job", cfg.db_path) == 0


class TestLogConcurrencySkip:
    def test_logs_warning(self, caplog):
        import logging
        exc = ConcurrencyLimitError("limit reached")
        with caplog.at_level(logging.WARNING, logger="cronwrap.concurrency_hooks"):
            log_concurrency_skip("my_job", exc)
        assert "my_job" in caplog.text
        assert "concurrency limit" in caplog.text
