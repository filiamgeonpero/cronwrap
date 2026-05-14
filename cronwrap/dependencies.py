"""Job dependency tracking — ensures jobs only run after their dependencies succeed."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwrap.history import JobHistory


@dataclass
class DependencyConfig:
    """Configuration for a job's dependencies."""
    requires: List[str] = field(default_factory=list)
    within_seconds: int = 86400  # default: dependency must have succeeded within 24h


def last_success_age(job_name: str, history: JobHistory) -> Optional[float]:
    """Return seconds since the last successful run of *job_name*, or None if never."""
    records = history.query(job_name, limit=50)
    for record in records:
        if record.exit_code == 0 and record.finished_at is not None:
            import time
            return time.time() - record.finished_at
    return None


def check_dependency(dep_name: str, within_seconds: int, history: JobHistory) -> bool:
    """Return True if *dep_name* succeeded within *within_seconds*."""
    age = last_success_age(dep_name, history)
    if age is None:
        return False
    return age <= within_seconds


def dependencies_met(
    config: DependencyConfig,
    history: JobHistory,
) -> Dict[str, bool]:
    """Check all dependencies; return a mapping of dep_name -> satisfied."""
    return {
        dep: check_dependency(dep, config.within_seconds, history)
        for dep in config.requires
    }


def all_dependencies_met(config: DependencyConfig, history: JobHistory) -> bool:
    """Return True only when every declared dependency is satisfied."""
    if not config.requires:
        return True
    return all(dependencies_met(config, history).values())


def unmet_dependencies(config: DependencyConfig, history: JobHistory) -> List[str]:
    """Return names of dependencies that are NOT currently satisfied."""
    return [
        name
        for name, ok in dependencies_met(config, history).items()
        if not ok
    ]
