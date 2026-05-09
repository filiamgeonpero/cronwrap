"""CLI sub-commands for tag-based job inspection."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from cronwrap.config import load_config
from cronwrap.tags import build_tag_index


def _load_index(config_path: str):
    cfg = load_config(config_path)
    jobs = cfg.get("jobs", [])
    return build_tag_index(jobs)


def cmd_list_tags(args: argparse.Namespace) -> None:
    """Print every registered tag, one per line."""
    index = _load_index(args.config)
    for tag in index.all_tags():
        print(tag)


def cmd_jobs_for_tag(args: argparse.Namespace) -> None:
    """Print jobs that match the supplied tag(s)."""
    index = _load_index(args.config)
    results: List[str] = index.jobs_for_tags(
        args.tags,
        match_all=args.all,
    )
    if not results:
        print("No jobs match.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(results))
    else:
        for name in results:
            print(name)


def build_parser(
    parser: Optional[argparse.ArgumentParser] = None,
) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(
            prog="cronwrap-tags",
            description="Inspect and filter jobs by tag.",
        )

    parser.add_argument(
        "--config",
        default="cronwrap.yaml",
        metavar="FILE",
        help="Path to cronwrap config file (default: cronwrap.yaml).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-tags", help="List all registered tags.").set_defaults(
        func=cmd_list_tags
    )

    p_jobs = sub.add_parser("jobs", help="List jobs matching one or more tags.")
    p_jobs.add_argument("tags", nargs="+", metavar="TAG", help="Tag(s) to filter by.")
    p_jobs.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Require ALL tags to match (intersection instead of union).",
    )
    p_jobs.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output results as a JSON array.",
    )
    p_jobs.set_defaults(func=cmd_jobs_for_tag)

    return parser


def main() -> None:  # pragma: no cover
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
