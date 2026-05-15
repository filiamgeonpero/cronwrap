"""Tests for cronwrap.lockfile and cronwrap.lockfile_hooks."""

import os
import pytest

from cronwrap.lockfile import (
    LockConfig,
    LockAcquireError,
    _lock_path,
    acquire_lock,
    release_lock,
    is_locked,
)
from cronwrap.lockfile_hooks import gate_on_lock


@pytest.fixture()
def lock_cfg(tmp_path):
    return LockConfig(enabled=True, lock_dir=str(tmp_path / "locks"))


# ---------------------------------------------------------------------------
# LockConfig defaults
# ---------------------------------------------------------------------------

class TestLockConfig:
    def test_defaults(self):
        cfg = LockConfig()
        assert cfg.enabled is True
        assert cfg.timeout_seconds == 0
        assert "cronwrap" in cfg.lock_dir


# ---------------------------------------------------------------------------
# acquire / release / is_locked
# ---------------------------------------------------------------------------

class TestAcquireRelease:
    def test_acquire_creates_file(self, lock_cfg):
        path = acquire_lock("my-job", lock_cfg)
        assert os.path.exists(path)

    def test_acquire_writes_pid(self, lock_cfg):
        path = acquire_lock("pid-job", lock_cfg)
        content = open(path).read().strip()
        assert content == str(os.getpid())

    def test_is_locked_true_after_acquire(self, lock_cfg):
        acquire_lock("live-job", lock_cfg)
        assert is_locked("live-job", lock_cfg) is True

    def test_is_locked_false_before_acquire(self, lock_cfg):
        assert is_locked("ghost-job", lock_cfg) is False

    def test_release_removes_file(self, lock_cfg):
        acquire_lock("rel-job", lock_cfg)
        release_lock("rel-job", lock_cfg)
        assert is_locked("rel-job", lock_cfg) is False

    def test_release_noop_when_not_locked(self, lock_cfg):
        # Should not raise
        release_lock("missing-job", lock_cfg)

    def test_double_acquire_raises(self, lock_cfg):
        acquire_lock("dup-job", lock_cfg)
        with pytest.raises(LockAcquireError):
            acquire_lock("dup-job", lock_cfg)

    def test_stale_lock_overwritten(self, lock_cfg, tmp_path):
        """A lock file referencing a non-existent PID should be replaced."""
        path = _lock_path(lock_cfg.lock_dir, "stale-job")
        os.makedirs(lock_cfg.lock_dir, exist_ok=True)
        with open(path, "w") as fh:
            fh.write("9999999")  # almost certainly not a real PID
        # Should succeed without raising
        acquire_lock("stale-job", lock_cfg)

    def test_disabled_config_returns_empty_path(self, lock_cfg):
        lock_cfg.enabled = False
        result = acquire_lock("disabled-job", lock_cfg)
        assert result == ""


# ---------------------------------------------------------------------------
# gate_on_lock hook
# ---------------------------------------------------------------------------

class TestGateOnLock:
    def test_runs_fn_and_returns_exit_code(self, lock_cfg):
        result = gate_on_lock("hook-job", lock_cfg, lambda: 0)
        assert result == 0

    def test_releases_lock_after_fn(self, lock_cfg):
        gate_on_lock("cleanup-job", lock_cfg, lambda: 0)
        assert is_locked("cleanup-job", lock_cfg) is False

    def test_returns_1_when_lock_held(self, lock_cfg):
        acquire_lock("busy-job", lock_cfg)
        result = gate_on_lock("busy-job", lock_cfg, lambda: 0)
        assert result == 1

    def test_no_config_runs_fn(self):
        called = []
        gate_on_lock("no-cfg", None, lambda: called.append(1) or 0)
        assert called == [1]
