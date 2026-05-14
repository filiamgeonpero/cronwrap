"""Tests for cronwrap.secrets."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from cronwrap.secrets import load_secrets_file, resolve_dict, resolve_value


# ---------------------------------------------------------------------------
# load_secrets_file
# ---------------------------------------------------------------------------


class TestLoadSecretsFile:
    def test_parses_simple_pairs(self, tmp_path: Path):
        f = tmp_path / "secrets.env"
        f.write_text("FOO=bar\nBAZ=qux\n")
        result = load_secrets_file(f)
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_ignores_comments(self, tmp_path: Path):
        f = tmp_path / "secrets.env"
        f.write_text("# comment\nKEY=value\n")
        result = load_secrets_file(f)
        assert "KEY" in result
        assert len(result) == 1

    def test_ignores_blank_lines(self, tmp_path: Path):
        f = tmp_path / "secrets.env"
        f.write_text("\nKEY=value\n\n")
        assert len(load_secrets_file(f)) == 1

    def test_strips_double_quotes(self, tmp_path: Path):
        f = tmp_path / "secrets.env"
        f.write_text('TOKEN="my secret"\n')
        assert load_secrets_file(f)["TOKEN"] == "my secret"

    def test_strips_single_quotes(self, tmp_path: Path):
        f = tmp_path / "secrets.env"
        f.write_text("TOKEN='my secret'\n")
        assert load_secrets_file(f)["TOKEN"] == "my secret"

    def test_ignores_lines_without_equals(self, tmp_path: Path):
        f = tmp_path / "secrets.env"
        f.write_text("NODIVIDER\nKEY=val\n")
        assert load_secrets_file(f) == {"KEY": "val"}


# ---------------------------------------------------------------------------
# resolve_value
# ---------------------------------------------------------------------------


class TestResolveValue:
    def test_no_references_unchanged(self):
        assert resolve_value("plain string") == "plain string"

    def test_resolves_from_extra(self):
        result = resolve_value("${DB_PASS}", extra={"DB_PASS": "secret123"})
        assert result == "secret123"

    def test_resolves_from_env(self, monkeypatch):
        monkeypatch.setenv("MY_TOKEN", "tok")
        assert resolve_value("${MY_TOKEN}") == "tok"

    def test_extra_takes_precedence_over_env(self, monkeypatch):
        monkeypatch.setenv("KEY", "from_env")
        result = resolve_value("${KEY}", extra={"KEY": "from_extra"})
        assert result == "from_extra"

    def test_unresolved_reference_left_as_is(self):
        result = resolve_value("${MISSING_KEY_XYZ}")
        assert result == "${MISSING_KEY_XYZ}"

    def test_multiple_references_in_one_string(self, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "5432")
        result = resolve_value("postgres://${HOST}:${PORT}/db")
        assert result == "postgres://localhost:5432/db"


# ---------------------------------------------------------------------------
# resolve_dict
# ---------------------------------------------------------------------------


class TestResolveDict:
    def test_resolves_all_values(self, monkeypatch):
        monkeypatch.setenv("SECRET", "s3cr3t")
        result = resolve_dict({"cmd": "run --token ${SECRET}", "plain": "ok"})
        assert result["cmd"] == "run --token s3cr3t"
        assert result["plain"] == "ok"

    def test_returns_new_dict(self):
        original = {"k": "v"}
        result = resolve_dict(original)
        assert result is not original
