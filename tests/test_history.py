"""Tests for cronwrap.history module."""

import os
import pytest
from cronwrap.history import JobHistory, ExecutionRecord


@pytest.fixture
def history(tmp_path):
    db_path = str(tmp_path / "test_history.db")
    return JobHistory(db_path=db_path)


class TestJobHistory:
    def test_record_start_returns_int(self, history):
        record_id = history.record_start("backup", "tar -czf /tmp/b.tar.gz /data")
        assert isinstance(record_id, int)
        assert record_id > 0

    def test_record_finish_stores_exit_code(self, history):
        rid = history.record_start("backup", "echo hello")
        history.record_finish(rid, exit_code=0, duration_seconds=1.23)
        records = history.get_recent("backup")
        assert len(records) == 1
        assert records[0].exit_code == 0
        assert records[0].success is True
        assert abs(records[0].duration_seconds - 1.23) < 0.001

    def test_record_finish_failure(self, history):
        rid = history.record_start("failing-job", "false")
        history.record_finish(rid, exit_code=1, duration_seconds=0.5, stderr_snippet="error!")
        records = history.get_recent("failing-job")
        assert records[0].success is False
        assert records[0].stderr_snippet == "error!"

    def test_get_recent_returns_correct_job(self, history):
        rid1 = history.record_start("job-a", "echo a")
        history.record_finish(rid1, exit_code=0, duration_seconds=0.1)
        rid2 = history.record_start("job-b", "echo b")
        history.record_finish(rid2, exit_code=0, duration_seconds=0.2)
        records = history.get_recent("job-a")
        assert len(records) == 1
        assert records[0].job_name == "job-a"

    def test_get_recent_limit(self, history):
        for i in range(5):
            rid = history.record_start("repeating", "echo loop")
            history.record_finish(rid, exit_code=0, duration_seconds=float(i))
        records = history.get_recent("repeating", limit=3)
        assert len(records) == 3

    def test_get_recent_ordered_desc(self, history):
        for _ in range(3):
            rid = history.record_start("ordered", "sleep 0")
            history.record_finish(rid, exit_code=0, duration_seconds=0.0)
        records = history.get_recent("ordered", limit=10)
        dates = [r.started_at for r in records]
        assert dates == sorted(dates, reverse=True)

    def test_last_success_returns_none_when_no_success(self, history):
        rid = history.record_start("never-ok", "false")
        history.record_finish(rid, exit_code=2, duration_seconds=0.1)
        assert history.last_success("never-ok") is None

    def test_last_success_returns_most_recent_ok(self, history):
        rid1 = history.record_start("mixed", "echo ok")
        history.record_finish(rid1, exit_code=0, duration_seconds=1.0)
        rid2 = history.record_start("mixed", "false")
        history.record_finish(rid2, exit_code=1, duration_seconds=0.5)
        rec = history.last_success("mixed")
        assert rec is not None
        assert rec.success is True

    def test_db_created_on_init(self, tmp_path):
        db_path = str(tmp_path / "subdir" / "history.db")
        _ = JobHistory(db_path=db_path)
        assert os.path.exists(db_path)
