"""Tests for cronwrap.config."""

import json
import os
import pytest

from cronwrap.config import JobConfig, config_from_env, load_config
from cronwrap.alerts import AlertConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def config_file(tmp_path):
    """Write a minimal valid config JSON and return its path."""
    data = {
        "command": "echo hello",
        "job_name": "test_job",
        "timeout": 60,
        "retries": 2,
        "alert_on_failure": True,
        "alert_config": {
            "smtp_host": "mail.test",
            "recipients": ["dev@test.com"],
        },
    }
    path = tmp_path / "job.json"
    path.write_text(json.dumps(data))
    return str(path)


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_command(self, config_file):
        cfg = load_config(config_file)
        assert cfg.command == "echo hello"

    def test_loads_nested_alert_config(self, config_file):
        cfg = load_config(config_file)
        assert cfg.alert_config.smtp_host == "mail.test"
        assert "dev@test.com" in cfg.alert_config.recipients

    def test_loads_retries(self, config_file):
        cfg = load_config(config_file)
        assert cfg.retries == 2

    def test_raises_for_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/job.json")

    def test_default_alert_config_when_absent(self, tmp_path):
        data = {"command": "ls"}
        path = tmp_path / "minimal.json"
        path.write_text(json.dumps(data))
        cfg = load_config(str(path))
        assert isinstance(cfg.alert_config, AlertConfig)


# ---------------------------------------------------------------------------
# config_from_env
# ---------------------------------------------------------------------------

class TestConfigFromEnv:
    def test_basic_defaults(self, monkeypatch):
        monkeypatch.delenv("CRONWRAP_JOB_NAME", raising=False)
        cfg = config_from_env("echo hi")
        assert cfg.command == "echo hi"
        assert cfg.job_name == "cron_job"
        assert cfg.retries == 0
        assert cfg.timeout is None

    def test_reads_env_vars(self, monkeypatch):
        monkeypatch.setenv("CRONWRAP_JOB_NAME", "my_job")
        monkeypatch.setenv("CRONWRAP_TIMEOUT", "120")
        monkeypatch.setenv("CRONWRAP_RETRIES", "3")
        monkeypatch.setenv("CRONWRAP_ALERT_ON_FAILURE", "true")
        monkeypatch.setenv("CRONWRAP_ALERT_RECIPIENTS", "a@b.com, c@d.com")
        cfg = config_from_env("echo env")
        assert cfg.job_name == "my_job"
        assert cfg.timeout == 120
        assert cfg.retries == 3
        assert cfg.alert_on_failure is True
        assert len(cfg.alert_config.recipients) == 2
