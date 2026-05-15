"""Utilities for capturing and truncating subprocess output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

DEFAULT_MAX_BYTES = 64 * 1024  # 64 KB


@dataclass
class CapturedOutput:
    """Holds stdout and stderr captured from a subprocess run."""

    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    def has_output(self) -> bool:
        """Return True if either stream contains non-whitespace content."""
        return bool(self.stdout.strip() or self.stderr.strip())

    def combined(self, separator: str = "\n") -> str:
        """Return stdout and stderr joined by *separator*, omitting empty streams."""
        parts = [s for s in (self.stdout, self.stderr) if s.strip()]
        return separator.join(parts)


def truncate(text: str, max_bytes: int = DEFAULT_MAX_BYTES) -> tuple[str, bool]:
    """Truncate *text* to at most *max_bytes* UTF-8 bytes.

    Returns a ``(result, was_truncated)`` tuple.
    """
    if max_bytes <= 0:
        return "", bool(text)
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text, False
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated, True


def capture_output(
    stdout_bytes: Optional[bytes],
    stderr_bytes: Optional[bytes],
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> CapturedOutput:
    """Decode raw bytes from a completed process into a :class:`CapturedOutput`.

    Each stream is independently truncated to *max_bytes*.
    """
    raw_stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
    raw_stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

    stdout, stdout_trunc = truncate(raw_stdout, max_bytes)
    stderr, stderr_trunc = truncate(raw_stderr, max_bytes)

    return CapturedOutput(
        stdout=stdout,
        stderr=stderr,
        stdout_truncated=stdout_trunc,
        stderr_truncated=stderr_trunc,
    )
