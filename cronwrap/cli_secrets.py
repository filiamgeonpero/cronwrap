"""CLI helpers for inspecting secret resolution.

Usage examples
--------------
    cronwrap-secrets check --secrets-file .secrets.env 'run --token ${DB_TOKEN}'
    cronwrap-secrets list-keys --secrets-file .secrets.env
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cronwrap.secrets import load_secrets_file, resolve_value, _REF_RE


def cmd_check(args: argparse.Namespace) -> int:
    """Resolve a value string and print the result."""
    extra: dict[str, str] = {}
    if args.secrets_file:
        try:
            extra = load_secrets_file(args.secrets_file)
        except FileNotFoundError:
            print(f"error: secrets file not found: {args.secrets_file}", file=sys.stderr)
            return 1

    resolved = resolve_value(args.value, extra=extra)
    unresolved = _REF_RE.findall(resolved)

    print(resolved)
    if unresolved:
        print(
            f"warning: {len(unresolved)} unresolved reference(s): {', '.join(unresolved)}",
            file=sys.stderr,
        )
        return 2
    return 0


def cmd_list_keys(args: argparse.Namespace) -> int:
    """List all keys defined in a secrets file."""
    try:
        secrets = load_secrets_file(args.secrets_file)
    except FileNotFoundError:
        print(f"error: secrets file not found: {args.secrets_file}", file=sys.stderr)
        return 1

    if not secrets:
        print("(no keys found)")
        return 0

    for key in sorted(secrets):
        print(key)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwrap-secrets",
        description="Inspect secret resolution for cronwrap jobs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Resolve a value and print it.")
    p_check.add_argument("value", help="String containing ${KEY} references.")
    p_check.add_argument("--secrets-file", metavar="PATH", help="Path to key=value secrets file.")
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser("list-keys", help="List keys in a secrets file.")
    p_list.add_argument("secrets_file", metavar="PATH", help="Path to key=value secrets file.")
    p_list.set_defaults(func=cmd_list_keys)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    main()
