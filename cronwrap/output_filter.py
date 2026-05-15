"""Filter and pattern-match captured output to suppress noise or detect anomalies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.output_capture import CapturedOutput


@dataclass
class OutputFilterConfig:
    """Configuration for output filtering rules."""

    suppress_patterns: List[str] = field(default_factory=list)
    alert_patterns: List[str] = field(default_factory=list)
    max_lines: int = 0  # 0 means unlimited


@dataclass
class FilterResult:
    """Result of applying an OutputFilterConfig to captured output."""

    stdout: str
    stderr: str
    suppressed_lines: int
    alert_matches: List[str]

    @property
    def has_alerts(self) -> bool:
        return len(self.alert_matches) > 0


def _filter_lines(
    text: str,
    suppress_patterns: List[re.Pattern],
    alert_patterns: List[re.Pattern],
    max_lines: int,
) -> tuple[str, int, List[str]]:
    """Return filtered text, suppressed line count, and alert matches."""
    lines = text.splitlines()
    kept: List[str] = []
    suppressed = 0
    alerts: List[str] = []

    for line in lines:
        if any(p.search(line) for p in suppress_patterns):
            suppressed += 1
            continue
        for p in alert_patterns:
            if p.search(line):
                alerts.append(line)
                break
        kept.append(line)

    if max_lines > 0:
        kept = kept[:max_lines]

    return "\n".join(kept), suppressed, alerts


def apply_filter(
    captured: CapturedOutput, config: Optional[OutputFilterConfig] = None
) -> FilterResult:
    """Apply *config* rules to *captured* output and return a FilterResult."""
    if config is None:
        config = OutputFilterConfig()

    suppress = [re.compile(p) for p in config.suppress_patterns]
    alert = [re.compile(p) for p in config.alert_patterns]

    filtered_stdout, sup_out, alerts_out = _filter_lines(
        captured.stdout, suppress, alert, config.max_lines
    )
    filtered_stderr, sup_err, alerts_err = _filter_lines(
        captured.stderr, suppress, alert, config.max_lines
    )

    return FilterResult(
        stdout=filtered_stdout,
        stderr=filtered_stderr,
        suppressed_lines=sup_out + sup_err,
        alert_matches=alerts_out + alerts_err,
    )
