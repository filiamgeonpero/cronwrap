"""Tests for cronwrap.retry."""

import pytest
from unittest.mock import MagicMock, patch

from cronwrap.retry import with_retry


class TestWithRetry:
    def test_returns_value_on_first_success(self):
        fn = MagicMock(return_value=42)
        result = with_retry(fn, retries=3)
        assert result == 42
        fn.assert_called_once()

    def test_no_retry_on_success(self):
        fn = MagicMock(return_value="ok")
        with_retry(fn, retries=0)
        fn.assert_called_once()

    def test_retries_on_failure_then_succeeds(self):
        fn = MagicMock(side_effect=[RuntimeError("fail"), RuntimeError("fail"), "done"])
        with patch("cronwrap.retry.time.sleep"):
            result = with_retry(fn, retries=2, delay=1.0)
        assert result == "done"
        assert fn.call_count == 3

    def test_raises_last_exception_when_all_fail(self):
        fn = MagicMock(side_effect=ValueError("boom"))
        with patch("cronwrap.retry.time.sleep"):
            with pytest.raises(ValueError, match="boom"):
                with_retry(fn, retries=2, delay=0.1)
        assert fn.call_count == 3

    def test_sleep_called_between_attempts(self):
        fn = MagicMock(side_effect=[OSError(), OSError(), "ok"])
        with patch("cronwrap.retry.time.sleep") as mock_sleep:
            with_retry(fn, retries=2, delay=2.0)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2.0)

    def test_backoff_multiplies_delay(self):
        fn = MagicMock(side_effect=[OSError(), OSError(), "ok"])
        with patch("cronwrap.retry.time.sleep") as mock_sleep:
            with_retry(fn, retries=2, delay=2.0, backoff=2.0)
        calls = [c.args[0] for c in mock_sleep.call_args_list]
        assert calls == [2.0, 4.0]

    def test_on_failure_callback_called_per_attempt(self):
        fn = MagicMock(side_effect=[RuntimeError("e1"), RuntimeError("e2"), "ok"])
        callback = MagicMock()
        with patch("cronwrap.retry.time.sleep"):
            with_retry(fn, retries=2, delay=0.0, on_failure=callback)
        assert callback.call_count == 2
        assert callback.call_args_list[0].args[0] == 0  # first attempt index
        assert isinstance(callback.call_args_list[0].args[1], RuntimeError)

    def test_invalid_retries_raises(self):
        with pytest.raises(ValueError, match="retries"):
            with_retry(lambda: None, retries=-1)

    def test_invalid_delay_raises(self):
        with pytest.raises(ValueError, match="delay"):
            with_retry(lambda: None, retries=0, delay=-1.0)

    def test_invalid_backoff_raises(self):
        with pytest.raises(ValueError, match="backoff"):
            with_retry(lambda: None, retries=0, backoff=0.5)

    def test_zero_retries_raises_immediately(self):
        fn = MagicMock(side_effect=KeyError("missing"))
        with pytest.raises(KeyError):
            with_retry(fn, retries=0)
        fn.assert_called_once()
