"""CLI entry point for cronwrap — inspect job history from the terminal."""

import argparse
import sys
from cronwrap.history import JobHistory, DEFAULT_DB_PATH


def _format_record(record) -> str:
    status = "OK" if record.success else "FAIL"
    duration = (
        f"{record.duration_seconds:.2f}s" if record.duration_seconds is not None else "N/A"
    )
    snippet = ""
    if record.stderr_snippet:
        snippet = f"  stderr: {record.stderr_snippet[:80]}"
    return (
        f"[{status}] {record.started_at}  exit={record.exit_code}  "
        f"duration={duration}{snippet}"
    )


def cmd_history(args) -> None:
    history = JobHistory(db_path=args.db)
    records = history.get_recent(args.job_name, limit=args.limit)
    if not records:
        print(f"No history found for job '{args.job_name}'.")
        return
    print(f"Last {len(records)} executions for '{args.job_name}':")
    for rec in records:
        print(" ", _format_record(rec))


def cmd_last_success(args) -> None:
    history = JobHistory(db_path=args.db)
    rec = history.last_success(args.job_name)
    if rec is None:
        print(f"No successful execution found for job '{args.job_name}'.")
        sys.exit(1)
    print(f"Last success for '{args.job_name}':")
    print(" ", _format_record(rec))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap",
        description="Cronwrap job management CLI",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="Path to the history SQLite database",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    hist = sub.add_parser("history", help="Show recent job execution history")
    hist.add_argument("job_name", help="Name of the cron job")
    hist.add_argument("-n", "--limit", type=int, default=10, help="Number of records")
    hist.set_defaults(func=cmd_history)

    ls = sub.add_parser("last-success", help="Show the last successful execution")
    ls.add_argument("job_name", help="Name of the cron job")
    ls.set_defaults(func=cmd_last_success)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
