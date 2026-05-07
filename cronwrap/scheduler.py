"""Simple cron expression parser and next-run scheduler."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


CRON_FIELDS = ("minute", "hour", "day", "month", "weekday")
_RANGES = {"minute": (0, 59), "hour": (0, 23), "day": (1, 31), "month": (1, 12), "weekday": (0, 6)}


def _parse_field(field: str, lo: int, hi: int) -> list[int]:
    """Expand a single cron field string into a sorted list of integers."""
    if field == "*":
        return list(range(lo, hi + 1))
    values: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, step_str = part.split("/", 1)
            step = int(step_str)
        if "-" in part:
            a, b = part.split("-", 1)
            values.update(range(int(a), int(b) + 1, step))
        elif part == "*":
            values.update(range(lo, hi + 1, step))
        else:
            values.add(int(part))
    if not all(lo <= v <= hi for v in values):
        raise ValueError(f"Field value out of range [{lo}, {hi}]: {field}")
    return sorted(values)


def parse_cron(expression: str) -> dict[str, list[int]]:
    """Parse a 5-field cron expression into a dict of allowed values."""
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Expected 5 cron fields, got {len(parts)}: {expression!r}")
    return {
        field: _parse_field(parts[i], *_RANGES[field])
        for i, field in enumerate(CRON_FIELDS)
    }


def next_run(expression: str, after: Optional[datetime] = None) -> datetime:
    """Return the next datetime matching *expression* strictly after *after*."""
    schedule = parse_cron(expression)
    dt = (after or datetime.now()).replace(second=0, microsecond=0) + timedelta(minutes=1)
    # Iterate up to 366 days worth of minutes before giving up.
    for _ in range(366 * 24 * 60):
        if (
            dt.month in schedule["month"]
            and dt.day in schedule["day"]
            and dt.weekday() in schedule["weekday"]
            and dt.hour in schedule["hour"]
            and dt.minute in schedule["minute"]
        ):
            return dt
        dt += timedelta(minutes=1)
    raise RuntimeError(f"Could not find next run time for expression: {expression!r}")


def is_due(expression: str, now: Optional[datetime] = None) -> bool:
    """Return True if *expression* matches the current minute."""
    dt = (now or datetime.now()).replace(second=0, microsecond=0)
    schedule = parse_cron(expression)
    return (
        dt.month in schedule["month"]
        and dt.day in schedule["day"]
        and dt.weekday() in schedule["weekday"]
        and dt.hour in schedule["hour"]
        and dt.minute in schedule["minute"]
    )
