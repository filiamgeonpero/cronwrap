"""CLI entry point for the cronwrap dashboard command."""
from __future__ import annotations

import argparse
import sys

from cronwrap.history import JobHistory
from cronwrap.dashboard import collect_status, render_dashboard


def build_dashboard_parser(parent: argparse.ArgumentParser | None = None) -> argparse.ArgumentParser:
    parser = parent or argparse.ArgumentParser(
        prog="cronwrap-dashboard",
        description="Display a status dashboard for cron jobs.",
    )
    parser.add_argument(
        "jobs",
        nargs="+",
        metavar="JOB",
        help="One or more job names to include in the dashboard.",
    )
    parser.add_argument(
        "--db",
        default="cronwrap_history.db",
        metavar="PATH",
        help="Path to the SQLite history database (default: cronwrap_history.db).",
    )
    parser.add_argument(
        "--output",
        choices=["text"],
        default="text",
        help="Output format (default: text).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_dashboard_parser()
    args = parser.parse_args(argv)

    history = JobHistory(db_path=args.db)
    statuses = collect_status(history, args.jobs)
    output = render_dashboard(statuses)
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
