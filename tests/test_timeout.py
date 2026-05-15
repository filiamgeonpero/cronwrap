"""Tests for cronwrap.timeout."""

import time
import pytest

from cronwrap.timeout import (
    TimeoutConfig,
    TimeoutExpired,
    enforce_timeout,
    timeout_for_config,
)


# ---------------------------------------------------------------------------
# TimeoutConfig
# ---------------------------------------------------------------------------

class TestTimeoutConfig:
    def test_defaults(self):
        cfg = TimeoutConfig()
        assert cfg.seconds == 0
        assert cfg.kill_on_timeout is True

    def test_enabled_false_when_zero(self):
        assert TimeoutConfig(seconds=0).enabled is False

    def test_enabled_true_when_positive(self):
        assert TimeoutConfig(seconds=5).enabled is True

    def test_custom_values(self):
        cfg = TimeoutConfig(seconds=30, kill_on_timeout=False)
        assert cfg.seconds == 30
        assert cfg.kill_on_timeout is False


# ---------------------------------------------------------------------------
# TimeoutExpired
# ---------------------------------------------------------------------------

class TestTimeoutExpired:
    def test_message_contains_job_name(self):
        exc = TimeoutExpired("my-job", 10)
        assert "my-job" in str(exc)

    def test_message_contains_seconds(self):
        exc = TimeoutExpired("my-job", 10)
        assert "10" in str(exc)

    def test_attributes(self):
        exc = TimeoutExpired("backup", 60)
        assert exc.job_name == "backup"
        assert exc.seconds == 60


# ---------------------------------------------------------------------------
# enforce_timeout
# ---------------------------------------------------------------------------

class TestEnforceTimeout:
    def test_no_timeout_when_disabled(self):
        cfg = TimeoutConfig(seconds=0)
        with enforce_timeout(cfg, "job"):
            time.sleep(0)  # should not raise

    def test_does_not_raise_when_fast_enough(self):
        cfg = TimeoutConfig(seconds=5)
        with enforce_timeout(cfg, "fast-job"):
            pass  # completes immediately

    def test_raises_timeout_expired(self):
        cfg = TimeoutConfig(seconds=1)
        with pytest.raises(TimeoutExpired) as exc_info:
            with enforce_timeout(cfg, "slow-job"):
                time.sleep(3)
        assert exc_info.value.job_name == "slow-job"
        assert exc_info.value.seconds == 1


# ---------------------------------------------------------------------------
# timeout_for_config
# ---------------------------------------------------------------------------

class TestTimeoutForConfig:
    def test_empty_dict_gives_zero_seconds(self):
        cfg = timeout_for_config({})
        assert cfg.seconds == 0

    def test_int_shorthand(self):
        cfg = timeout_for_config({"timeout": 45})
        assert cfg.seconds == 45

    def test_section_dict(self):
        cfg = timeout_for_config({"timeout": {"seconds": 120, "kill_on_timeout": False}})
        assert cfg.seconds == 120
        assert cfg.kill_on_timeout is False

    def test_defaults_kill_on_timeout(self):
        cfg = timeout_for_config({"timeout": {"seconds": 10}})
        assert cfg.kill_on_timeout is True
