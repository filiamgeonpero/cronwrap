"""Tests for cronwrap.output_filter."""

import pytest

from cronwrap.output_capture import CapturedOutput
from cronwrap.output_filter import (
    FilterResult,
    OutputFilterConfig,
    apply_filter,
)


def _captured(stdout: str = "", stderr: str = "") -> CapturedOutput:
    return CapturedOutput(stdout=stdout, stderr=stderr)


# ---------------------------------------------------------------------------
# OutputFilterConfig defaults
# ---------------------------------------------------------------------------

class TestOutputFilterConfig:
    def test_defaults(self):
        cfg = OutputFilterConfig()
        assert cfg.suppress_patterns == []
        assert cfg.alert_patterns == []
        assert cfg.max_lines == 0

    def test_custom_values(self):
        cfg = OutputFilterConfig(
            suppress_patterns=[r"DEBUG"],
            alert_patterns=[r"ERROR"],
            max_lines=50,
        )
        assert cfg.suppress_patterns == [r"DEBUG"]
        assert cfg.alert_patterns == [r"ERROR"]
        assert cfg.max_lines == 50


# ---------------------------------------------------------------------------
# apply_filter — basic passthrough
# ---------------------------------------------------------------------------

def test_no_config_returns_original_text():
    cap = _captured(stdout="hello\nworld", stderr="")
    result = apply_filter(cap)
    assert result.stdout == "hello\nworld"
    assert result.suppressed_lines == 0
    assert result.alert_matches == []


def test_empty_output_returns_empty():
    result = apply_filter(_captured())
    assert result.stdout == ""
    assert result.stderr == ""


# ---------------------------------------------------------------------------
# Suppress patterns
# ---------------------------------------------------------------------------

def test_suppress_removes_matching_lines():
    cap = _captured(stdout="INFO: ok\nDEBUG: noise\nINFO: done")
    cfg = OutputFilterConfig(suppress_patterns=[r"DEBUG"])
    result = apply_filter(cap, cfg)
    assert "DEBUG" not in result.stdout
    assert result.suppressed_lines == 1


def test_suppress_counts_stderr_lines():
    cap = _captured(stderr="DEBUG: a\nDEBUG: b\nERROR: c")
    cfg = OutputFilterConfig(suppress_patterns=[r"DEBUG"])
    result = apply_filter(cap, cfg)
    assert result.suppressed_lines == 2


def test_suppress_multiple_patterns():
    cap = _captured(stdout="TRACE: x\nDEBUG: y\nINFO: z")
    cfg = OutputFilterConfig(suppress_patterns=[r"TRACE", r"DEBUG"])
    result = apply_filter(cap, cfg)
    assert result.suppressed_lines == 2
    assert result.stdout == "INFO: z"


# ---------------------------------------------------------------------------
# Alert patterns
# ---------------------------------------------------------------------------

def test_alert_pattern_detects_match():
    cap = _captured(stdout="INFO: running\nERROR: disk full")
    cfg = OutputFilterConfig(alert_patterns=[r"ERROR"])
    result = apply_filter(cap, cfg)
    assert result.has_alerts
    assert any("disk full" in m for m in result.alert_matches)


def test_no_alert_when_no_match():
    cap = _captured(stdout="INFO: all good")
    cfg = OutputFilterConfig(alert_patterns=[r"CRITICAL"])
    result = apply_filter(cap, cfg)
    assert not result.has_alerts


def test_alert_matches_from_stderr():
    cap = _captured(stderr="CRITICAL: out of memory")
    cfg = OutputFilterConfig(alert_patterns=[r"CRITICAL"])
    result = apply_filter(cap, cfg)
    assert result.has_alerts


# ---------------------------------------------------------------------------
# max_lines truncation
# ---------------------------------------------------------------------------

def test_max_lines_truncates_stdout():
    lines = "\n".join(f"line {i}" for i in range(10))
    cap = _captured(stdout=lines)
    cfg = OutputFilterConfig(max_lines=3)
    result = apply_filter(cap, cfg)
    assert len(result.stdout.splitlines()) == 3


def test_max_lines_zero_means_unlimited():
    lines = "\n".join(f"line {i}" for i in range(20))
    cap = _captured(stdout=lines)
    cfg = OutputFilterConfig(max_lines=0)
    result = apply_filter(cap, cfg)
    assert len(result.stdout.splitlines()) == 20
