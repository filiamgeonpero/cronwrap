"""Tests for cronwrap.tags."""
import pytest

from cronwrap.tags import TagIndex, build_tag_index


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def index() -> TagIndex:
    idx = TagIndex()
    idx.register("backup", ["daily", "storage"])
    idx.register("report", ["daily", "email"])
    idx.register("cleanup", ["storage", "weekly"])
    return idx


# ---------------------------------------------------------------------------
# TagIndex.register / jobs_for_tag
# ---------------------------------------------------------------------------

class TestTagIndex:
    def test_jobs_for_known_tag(self, index: TagIndex) -> None:
        assert set(index.jobs_for_tag("daily")) == {"backup", "report"}

    def test_jobs_for_unknown_tag_returns_empty(self, index: TagIndex) -> None:
        assert index.jobs_for_tag("nonexistent") == []

    def test_register_appends(self, index: TagIndex) -> None:
        index.register("sync", ["daily"])
        assert "sync" in index.jobs_for_tag("daily")

    def test_all_tags_sorted(self, index: TagIndex) -> None:
        assert index.all_tags() == ["daily", "email", "storage", "weekly"]


# ---------------------------------------------------------------------------
# TagIndex.jobs_for_tags  (union / intersection)
# ---------------------------------------------------------------------------

class TestJobsForTags:
    def test_union_returns_any_match(self, index: TagIndex) -> None:
        result = index.jobs_for_tags(["email", "weekly"])
        assert set(result) == {"report", "cleanup"}

    def test_intersection_requires_all_tags(self, index: TagIndex) -> None:
        result = index.jobs_for_tags(["daily", "storage"], match_all=True)
        assert result == ["backup"]

    def test_empty_tags_returns_empty(self, index: TagIndex) -> None:
        assert index.jobs_for_tags([]) == []

    def test_no_intersection_returns_empty(self, index: TagIndex) -> None:
        result = index.jobs_for_tags(["email", "weekly"], match_all=True)
        assert result == []

    def test_result_is_sorted(self, index: TagIndex) -> None:
        result = index.jobs_for_tags(["daily"])
        assert result == sorted(result)


# ---------------------------------------------------------------------------
# build_tag_index
# ---------------------------------------------------------------------------

class TestBuildTagIndex:
    def test_builds_from_job_dicts(self) -> None:
        jobs = [
            {"name": "alpha", "tags": ["critical"]},
            {"name": "beta", "tags": ["critical", "slow"]},
        ]
        idx = build_tag_index(jobs)
        assert set(idx.jobs_for_tag("critical")) == {"alpha", "beta"}

    def test_skips_jobs_without_tags(self) -> None:
        jobs = [
            {"name": "alpha"},
            {"name": "beta", "tags": ["nightly"]},
        ]
        idx = build_tag_index(jobs)
        assert idx.jobs_for_tag("nightly") == ["beta"]
        assert idx.all_tags() == ["nightly"]

    def test_custom_keys(self) -> None:
        jobs = [{"job": "gamma", "labels": ["fast"]}]
        idx = build_tag_index(jobs, name_key="job", tags_key="labels")
        assert idx.jobs_for_tag("fast") == ["gamma"]
