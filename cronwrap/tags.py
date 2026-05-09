"""Tag-based filtering and grouping for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass
class TagIndex:
    """Maps tags to job names for fast lookup."""

    _index: Dict[str, List[str]] = field(default_factory=dict)

    def register(self, job_name: str, tags: Iterable[str]) -> None:
        """Associate *job_name* with each tag in *tags*."""
        for tag in tags:
            self._index.setdefault(tag, []).append(job_name)

    def jobs_for_tag(self, tag: str) -> List[str]:
        """Return all job names associated with *tag* (empty list if unknown)."""
        return list(self._index.get(tag, []))

    def jobs_for_tags(
        self,
        tags: Iterable[str],
        *,
        match_all: bool = False,
    ) -> List[str]:
        """Return job names matching *tags*.

        Args:
            tags: Tags to filter by.
            match_all: When *True* only jobs that have **all** supplied tags
                       are returned; otherwise any matching tag is sufficient.
        """
        tag_list = list(tags)
        if not tag_list:
            return []

        sets = [set(self.jobs_for_tag(t)) for t in tag_list]
        if match_all:
            result = sets[0].intersection(*sets[1:])
        else:
            result = sets[0].union(*sets[1:])
        return sorted(result)

    def all_tags(self) -> List[str]:
        """Return a sorted list of every registered tag."""
        return sorted(self._index.keys())


def build_tag_index(
    jobs: Iterable[Dict],
    *,
    name_key: str = "name",
    tags_key: str = "tags",
) -> TagIndex:
    """Build a :class:`TagIndex` from an iterable of job config dicts.

    Each dict is expected to have at minimum a *name_key* entry.  The
    *tags_key* entry is optional; jobs without it are silently skipped.
    """
    index = TagIndex()
    for job in jobs:
        name: Optional[str] = job.get(name_key)
        tags: Optional[List[str]] = job.get(tags_key)
        if name and tags:
            index.register(name, tags)
    return index
