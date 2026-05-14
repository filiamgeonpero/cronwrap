"""Hooks that integrate dependency checks into the runner lifecycle."""
from __future__ import annotations

import logging
from typing import Optional

from cronwrap.dependencies import DependencyConfig, all_dependencies_met, unmet_dependencies
from cronwrap.history import JobHistory

logger = logging.getLogger(__name__)


def gate_on_dependencies(
    job_name: str,
    dep_config: Optional[DependencyConfig],
    history: JobHistory,
) -> bool:
    """Return True if the job is allowed to run (all deps satisfied or none declared).

    Logs a warning listing any unmet dependencies when the job is blocked.
    """
    if dep_config is None or not dep_config.requires:
        return True

    if all_dependencies_met(dep_config, history):
        logger.debug(
            "[%s] all dependencies satisfied: %s",
            job_name,
            dep_config.requires,
        )
        return True

    unmet = unmet_dependencies(dep_config, history)
    logger.warning(
        "[%s] skipped — unmet dependencies: %s (required within %ds)",
        job_name,
        unmet,
        dep_config.within_seconds,
    )
    return False


def log_dependency_skip(job_name: str, unmet: list[str]) -> None:
    """Emit a structured log entry when a job is skipped due to dependencies."""
    logger.info(
        "dependency_skip job=%s unmet=%s",
        job_name,
        ",".join(unmet),
    )
