"""Tests for cronwrap.audit."""

from __future__ import annotations

import pytest
from pathlib import Path

from cronwrap.audit import AuditEvent, AuditLog, make_event


@pytest.fixture()
def audit_log(tmp_path: Path) -> AuditLog:
    log = AuditLog(db_path=tmp_path / "audit.db")
    yield log
    log.close()


class TestAuditLog:
    def test_record_returns_int(self, audit_log: AuditLog) -> None:
        event = make_event("backup", "start")
        row_id = audit_log.record(event)
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_query_returns_recorded_event(self, audit_log: AuditLog) -> None:
        audit_log.record(make_event("backup", "success", exit_code=0))
        results = audit_log.query("backup")
        assert len(results) == 1
        assert results[0].event_type == "success"
        assert results[0].exit_code == 0

    def test_query_filters_by_event_type(self, audit_log: AuditLog) -> None:
        audit_log.record(make_event("backup", "start"))
        audit_log.record(make_event("backup", "failure", exit_code=1))
        results = audit_log.query("backup", event_type="failure")
        assert len(results) == 1
        assert results[0].event_type == "failure"

    def test_query_respects_limit(self, audit_log: AuditLog) -> None:
        for _ in range(10):
            audit_log.record(make_event("backup", "success"))
        results = audit_log.query("backup", limit=3)
        assert len(results) == 3

    def test_query_isolates_by_job_name(self, audit_log: AuditLog) -> None:
        audit_log.record(make_event("backup", "success"))
        audit_log.record(make_event("report", "success"))
        results = audit_log.query("backup")
        assert all(r.job_name == "backup" for r in results)

    def test_query_returns_newest_first(self, audit_log: AuditLog) -> None:
        audit_log.record(make_event("backup", "start"))
        audit_log.record(make_event("backup", "success"))
        results = audit_log.query("backup")
        assert results[0].event_type == "success"

    def test_attempt_stored(self, audit_log: AuditLog) -> None:
        audit_log.record(make_event("backup", "retry", attempt=3))
        results = audit_log.query("backup")
        assert results[0].attempt == 3

    def test_detail_stored(self, audit_log: AuditLog) -> None:
        audit_log.record(make_event("backup", "failure", detail="disk full"))
        results = audit_log.query("backup")
        assert results[0].detail == "disk full"


class TestMakeEvent:
    def test_sets_job_name(self) -> None:
        ev = make_event("myjob", "start")
        assert ev.job_name == "myjob"

    def test_sets_event_type(self) -> None:
        ev = make_event("myjob", "timeout")
        assert ev.event_type == "timeout"

    def test_timestamp_is_iso_string(self) -> None:
        ev = make_event("myjob", "start")
        # Should not raise
        from datetime import datetime
        datetime.fromisoformat(ev.timestamp)

    def test_defaults(self) -> None:
        ev = make_event("myjob", "start")
        assert ev.detail is None
        assert ev.exit_code is None
        assert ev.attempt == 1
