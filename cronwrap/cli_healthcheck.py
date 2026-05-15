"""CLI sub-command: cronwrap-health — report job health status."""
from __future__ import annotations

import argparse
import sys

from cronwrap.healthcheck import check_health, render_health
from cronwrap.history import JobHistory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-health",
        description="Report health status for one or more cron jobs.",
    )
    parser.add_argument(
        "jobs",
        nargs="+",
        metavar="JOB",
        help="Job name(s) to check.",
    )
    parser.add_argument(
        "--db",
        default="cronwrap_history.db",
        metavar="PATH",
        help="Path to the history SQLite database (default: cronwrap_history.db).",
    )
    parser.add_argument(
        "--max-age",
        type=float,
        default=0,
        metavar="SECONDS",
        help="Mark job unhealthy if last success is older than this many seconds.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit with code 1 as soon as any job is unhealthy.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    history = JobHistory(db_path=args.db)
    statuses = [
        check_health(job, history, max_age_seconds=args.max_age)
        for job in args.jobs
    ]

    print(render_health(statuses))

    unhealthy = [s for s in statuses if not s.healthy]
    if unhealthy:
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
