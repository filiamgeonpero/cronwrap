"""Tests for cronwrap.scheduler."""

import pytest
from datetime import datetime

from cronwrap.scheduler import parse_cron, next_run, is_due


class TestParseCron:
    def test_wildcard_minute(self):
        result = parse_cron("* * * * *")
        assert result["minute"] == list(range(0, 60))

    def test_specific_values(self):
        result = parse_cron("5 3 * * *")
        assert result["minute"] == [5]
        assert result["hour"] == [3]

    def test_range(self):
        result = parse_cron("0-4 * * * *")
        assert result["minute"] == [0, 1, 2, 3, 4]

    def test_step(self):
        result = parse_cron("*/15 * * * *")
        assert result["minute"] == [0, 15, 30, 45]

    def test_list(self):
        result = parse_cron("1,2,3 * * * *")
        assert result["minute"] == [1, 2, 3]

    def test_invalid_field_count_raises(self):
        with pytest.raises(ValueError, match="Expected 5 cron fields"):
            parse_cron("* * * *")

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_cron("60 * * * *")


class TestNextRun:
    def test_next_minute(self):
        base = datetime(2024, 1, 15, 12, 0, 0)
        result = next_run("* * * * *", after=base)
        assert result == datetime(2024, 1, 15, 12, 1, 0)

    def test_hourly(self):
        base = datetime(2024, 1, 15, 12, 5, 0)
        result = next_run("0 * * * *", after=base)
        assert result == datetime(2024, 1, 15, 13, 0, 0)

    def test_daily_midnight(self):
        base = datetime(2024, 1, 15, 0, 1, 0)
        result = next_run("0 0 * * *", after=base)
        assert result == datetime(2024, 1, 16, 0, 0, 0)

    def test_specific_weekday(self):
        # 2024-01-15 is Monday (weekday=0)
        base = datetime(2024, 1, 15, 0, 0, 0)
        result = next_run("0 9 * * 5", after=base)  # next Friday 09:00
        assert result.weekday() == 4  # Friday
        assert result.hour == 9
        assert result.minute == 0

    def test_returns_datetime(self):
        base = datetime(2024, 6, 1, 0, 0, 0)
        result = next_run("30 6 * * *", after=base)
        assert isinstance(result, datetime)
        assert result > base


class TestIsDue:
    def test_matching_expression(self):
        dt = datetime(2024, 3, 10, 14, 30)
        assert is_due("30 14 * * *", now=dt) is True

    def test_non_matching_expression(self):
        dt = datetime(2024, 3, 10, 14, 31)
        assert is_due("30 14 * * *", now=dt) is False

    def test_wildcard_always_due(self):
        dt = datetime(2024, 7, 4, 23, 59)
        assert is_due("* * * * *", now=dt) is True
