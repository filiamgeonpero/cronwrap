"""Tests for cronwrap.output_capture."""

import pytest

from cronwrap.output_capture import (
    DEFAULT_MAX_BYTES,
    CapturedOutput,
    capture_output,
    truncate,
)


class TestCapturedOutput:
    def test_has_output_false_when_empty(self):
        co = CapturedOutput()
        assert co.has_output() is False

    def test_has_output_true_with_stdout(self):
        co = CapturedOutput(stdout="hello")
        assert co.has_output() is True

    def test_has_output_true_with_stderr(self):
        co = CapturedOutput(stderr="oops")
        assert co.has_output() is True

    def test_has_output_false_whitespace_only(self):
        co = CapturedOutput(stdout="   ", stderr="\n")
        assert co.has_output() is False

    def test_combined_both_streams(self):
        co = CapturedOutput(stdout="out", stderr="err")
        assert co.combined() == "out\nerr"

    def test_combined_skips_empty_stderr(self):
        co = CapturedOutput(stdout="only stdout", stderr="")
        assert co.combined() == "only stdout"

    def test_combined_custom_separator(self):
        co = CapturedOutput(stdout="a", stderr="b")
        assert co.combined(separator=" | ") == "a | b"


class TestTruncate:
    def test_short_text_unchanged(self):
        result, truncated = truncate("hello", max_bytes=100)
        assert result == "hello"
        assert truncated is False

    def test_long_text_is_truncated(self):
        text = "x" * 200
        result, truncated = truncate(text, max_bytes=100)
        assert len(result.encode("utf-8")) <= 100
        assert truncated is True

    def test_exact_length_not_truncated(self):
        text = "a" * 10
        result, truncated = truncate(text, max_bytes=10)
        assert result == text
        assert truncated is False

    def test_zero_max_bytes_returns_empty(self):
        result, truncated = truncate("hello", max_bytes=0)
        assert result == ""
        assert truncated is True

    def test_empty_string_not_truncated(self):
        result, truncated = truncate("", max_bytes=100)
        assert result == ""
        assert truncated is False


class TestCaptureOutput:
    def test_decodes_stdout_and_stderr(self):
        co = capture_output(b"hello", b"world")
        assert co.stdout == "hello"
        assert co.stderr == "world"

    def test_none_bytes_treated_as_empty(self):
        co = capture_output(None, None)
        assert co.stdout == ""
        assert co.stderr == ""

    def test_truncation_flags_set(self):
        big = b"z" * (DEFAULT_MAX_BYTES + 1)
        co = capture_output(big, b"small")
        assert co.stdout_truncated is True
        assert co.stderr_truncated is False

    def test_custom_max_bytes(self):
        co = capture_output(b"abcdef", b"xyz", max_bytes=3)
        assert len(co.stdout.encode("utf-8")) <= 3
        assert co.stdout_truncated is True
        assert co.stderr_truncated is True

    def test_invalid_utf8_replaced(self):
        co = capture_output(b"\xff\xfe", b"ok")
        assert isinstance(co.stdout, str)
        assert co.stderr == "ok"
