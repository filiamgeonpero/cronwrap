"""Secrets resolution for job commands and config values.

Supports resolving secret references from environment variables
or from a simple key=value secrets file.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

_REF_RE = re.compile(r"\$\{([^}]+)\}")


def load_secrets_file(path: str | Path) -> dict[str, str]:
    """Parse a key=value secrets file and return a dict.

    Lines starting with '#' and blank lines are ignored.
    Values may optionally be quoted with single or double quotes.
    """
    secrets: dict[str, str] = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        secrets[key] = value
    return secrets


def resolve_value(
    value: str,
    extra: Optional[dict[str, str]] = None,
) -> str:
    """Replace all ${KEY} references in *value*.

    Resolution order:
    1. *extra* mapping (e.g. loaded from a secrets file)
    2. Process environment variables

    Unresolved references are left as-is.
    """
    if extra is None:
        extra = {}

    def _replace(match: re.Match) -> str:
        key = match.group(1)
        if key in extra:
            return extra[key]
        return os.environ.get(key, match.group(0))

    return _REF_RE.sub(_replace, value)


def resolve_dict(
    mapping: dict[str, str],
    extra: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """Return a new dict with all values resolved."""
    return {k: resolve_value(v, extra) for k, v in mapping.items()}
