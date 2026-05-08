"""Simple text-based status dashboard for cronwrap jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from cronwrap.history import JobHistory
from cronwrap.metrics import compute_metrics, format_metrics


@dataclass
class JobStatus:
    name: str
    last_run: Optional[datetime]
    last_exit_code: Optional[int]
    total_runs: int
    success_rate: float
    avg_duration_s: float

    @property
    def state(self) -> str:
        if self.last_exit_code is None:
            return "NEVER RUN"
        return "OK" if self.last_exit_code == 0 else "FAILED"


def collect_status(history: JobHistory, job_names: List[str]) -> List[JobStatus]:
    """Return a JobStatus for each named job."""
    statuses: List[JobStatus] = []
    for name in job_names:
        records = history.get_history(name, limit=200)
        metrics = compute_metrics(records)
        last = records[0] if records else None
        statuses.append(
            JobStatus(
                name=name,
                last_run=datetime.fromisoformat(last.started_at) if last else None,
                last_exit_code=last.exit_code if last else None,
                total_runs=metrics.total_runs,
                success_rate=metrics.success_rate,
                avg_duration_s=metrics.avg_duration_s,
            )
        )
    return statuses


def render_dashboard(statuses: List[JobStatus]) -> str:
    """Render a plain-text dashboard table."""
    if not statuses:
        return "No jobs to display.\n"

    col_name = max(len(s.name) for s in statuses)
    col_name = max(col_name, 4)
    header = (
        f"{'JOB':<{col_name}}  {'STATE':<10}  {'LAST RUN':<20}"
        f"  {'RUNS':>5}  {'SUCCESS%':>9}  {'AVG(s)':>7}"
    )
    sep = "-" * len(header)
    lines = [header, sep]
    for s in statuses:
        last_run_str = s.last_run.strftime("%Y-%m-%d %H:%M:%S") if s.last_run else "—"
        lines.append(
            f"{s.name:<{col_name}}  {s.state:<10}  {last_run_str:<20}"
            f"  {s.total_runs:>5}  {s.success_rate * 100:>8.1f}%  {s.avg_duration_s:>7.2f}"
        )
    lines.append("")
    return "\n".join(lines)
