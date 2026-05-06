"""Execution metrics aggregation for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwrap.history import JobHistory


@dataclass
class JobMetrics:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_duration_seconds: Optional[float]
    min_duration_seconds: Optional[float]
    max_duration_seconds: Optional[float]
    last_exit_code: Optional[int]


def compute_metrics(job_name: str, history: JobHistory, limit: int = 100) -> JobMetrics:
    """Compute aggregated metrics for a job from its execution history."""
    records = history.get_history(job_name, limit=limit)

    total = len(records)
    if total == 0:
        return JobMetrics(
            job_name=job_name,
            total_runs=0,
            successful_runs=0,
            failed_runs=0,
            success_rate=0.0,
            avg_duration_seconds=None,
            min_duration_seconds=None,
            max_duration_seconds=None,
            last_exit_code=None,
        )

    successful = [r for r in records if r.exit_code == 0]
    failed = [r for r in records if r.exit_code is not None and r.exit_code != 0]

    durations: List[float] = [
        r.duration_seconds
        for r in records
        if r.duration_seconds is not None
    ]

    avg_dur = sum(durations) / len(durations) if durations else None
    min_dur = min(durations) if durations else None
    max_dur = max(durations) if durations else None

    last_exit = records[0].exit_code if records else None

    return JobMetrics(
        job_name=job_name,
        total_runs=total,
        successful_runs=len(successful),
        failed_runs=len(failed),
        success_rate=len(successful) / total * 100.0,
        avg_duration_seconds=avg_dur,
        min_duration_seconds=min_dur,
        max_duration_seconds=max_dur,
        last_exit_code=last_exit,
    )


def format_metrics(metrics: JobMetrics) -> str:
    """Return a human-readable summary of job metrics."""
    lines = [
        f"Metrics for '{metrics.job_name}'",
        f"  Total runs     : {metrics.total_runs}",
        f"  Successful     : {metrics.successful_runs}",
        f"  Failed         : {metrics.failed_runs}",
        f"  Success rate   : {metrics.success_rate:.1f}%",
    ]
    if metrics.avg_duration_seconds is not None:
        lines.append(f"  Avg duration   : {metrics.avg_duration_seconds:.2f}s")
        lines.append(f"  Min duration   : {metrics.min_duration_seconds:.2f}s")
        lines.append(f"  Max duration   : {metrics.max_duration_seconds:.2f}s")
    if metrics.last_exit_code is not None:
        lines.append(f"  Last exit code : {metrics.last_exit_code}")
    return "\n".join(lines)
