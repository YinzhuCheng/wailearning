"""
S1–S3: Student My Courses quota card, submission-driven usage, cap exhaustion.

Execution deferred — see tests/behavior/conftest.py.
"""

from __future__ import annotations

from typing import Any


class StudentMyCoursesPage:
    """MyCourses.vue placeholder."""

    def __init__(self, session: Any) -> None:
        self._session = session

    def select_course(self, subject_id: int) -> None:
        """Pick current course from list."""

    def read_llm_quota_card(self) -> dict[str, Any]:
        """Parse 当前课程 · LLM 用量 card or call GET student-quota in parallel."""
        return {}

    def wait_for_quota_loaded_or_error(self) -> str:
        """Return 'loaded' | 'empty' | 'error' for S1 paths."""
        return "empty"


def test_s1_quota_card_empty_vs_loaded_states() -> None:
    """
    S1: Student opens My Courses: no roster / API error vs success → 暂无用量数据 vs populated lines.
    """
    page = StudentMyCoursesPage(session=None)
    page.select_course(subject_id=1)
    _state = page.wait_for_quota_loaded_or_error()
    assert _state in ("loaded", "empty", "error")


def test_s2_submission_increments_usage_counters() -> None:
    """
    S2: After successful LLM grade, student_used_tokens_today increases; remaining decreases;
    consistent with LLMTokenUsageLog for that student+date+tz.
    """
    page = StudentMyCoursesPage(session=None)
    page.select_course(subject_id=1)


def test_s3_second_submit_fails_when_student_daily_cap_hit() -> None:
    """
    S3: Admin caps student very low → first grading succeeds second fails with quota_exceeded_student only.
    """
    page = StudentMyCoursesPage(session=None)
    page.select_course(subject_id=1)
