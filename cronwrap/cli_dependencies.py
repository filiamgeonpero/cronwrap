"""CLI sub-commands for inspecting job dependency status."""
from __future__ import annotations

import argparse
import sys
from typing import List

from cronwrap.dependencies import DependencyConfig, dependencies_met
from cronwrap.history import JobHistory


def _build_dep_config(args: argparse.Namespace) -> DependencyConfig:
    return DependencyConfig(
        requires=args.requires,
        within_seconds=args.within,
    )


def cmd_check(args: argparse.Namespace) -> int:
    """Print dependency status for a job and exit non-zero if any are unmet."""
    history = JobHistory(args.db)
    cfg = _build_dep_config(args)
    status = dependencies_met(cfg, history)

    all_ok = True
    for dep, ok in status.items():
        mark = "OK  " if ok else "FAIL"
        print(f"[{mark}] {dep}")
        if not ok:
            all_ok = False

    if not status:
        print("No dependencies declared.")

    return 0 if all_ok else 1


def build_parser(parent: argparse._SubParsersAction | None = None) -> argparse.ArgumentParser:
    description = "Inspect job dependency satisfaction."
    if parent is not None:
        parser = parent.add_parser("dependencies", help=description)
    else:
        parser = argparse.ArgumentParser(
            prog="cronwrap-dependencies",
            description=description,
        )

    sub = parser.add_subparsers(dest="dep_cmd", required=True)

    check = sub.add_parser("check", help="Check whether dependencies are met")
    check.add_argument("--db", default="cronwrap.db", help="Path to history DB")
    check.add_argument(
        "--requires",
        nargs="+",
        required=True,
        metavar="JOB",
        help="Dependency job names",
    )
    check.add_argument(
        "--within",
        type=int,
        default=86400,
        metavar="SECONDS",
        help="Success must be within this many seconds (default: 86400)",
    )
    check.set_defaults(func=cmd_check)

    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()
