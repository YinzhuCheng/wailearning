"""
T1–T3: Teacher course LLM config vs global admin policy.

Execution deferred — see tests/behavior/conftest.py.
"""

from __future__ import annotations

from typing import Any


class TeacherCourseLlmDialog:
    """Subjects.vue LLM dialog placeholder (next round: Playwright)."""

    def __init__(self, course_id: int, session: Any) -> None:
        self.course_id = course_id
        self._session = session

    def open_for_course(self, course_name: str) -> None:
        """Login as teacher → course list → open LLM config for named course."""

    def save_payload_with_legacy_extra_fields(self, payload: dict[str, Any]) -> Any:
        """
        PUT /api/llm-settings/courses/{id} with obsolete keys e.g. daily_course_token_limit.
        Expect 200 and server ignore (CourseLLMConfigUpdate extra=ignore).
        """
        return None

    def set_course_quota_timezone_archive(self, value: str) -> None:
        """Set 额度时区 field (display-only vs global billing)."""

    def toggle_auto_grading_and_endpoints(self, enabled: bool, endpoint_preset_ids: list[int]) -> None:
        """Toggle is_enabled, bind endpoints / groups."""


def test_t1_teacher_save_with_legacy_course_token_fields_ignored() -> None:
    """
    T1: Teacher UI (or API client) sends daily_course_token_limit; response 200; no course pool behavior.
    """
    dlg = TeacherCourseLlmDialog(course_id=1, session=None)
    dlg.save_payload_with_legacy_extra_fields(
        {
            "is_enabled": True,
            "daily_course_token_limit": 999999,
            "estimated_chars_per_token": 4.0,
            "endpoints": [{"preset_id": 1, "priority": 1}],
        }
    )


def test_t2_course_archive_timezone_diverges_from_global_calendar() -> None:
    """
    T2: Teacher sets course quota_timezone=UTC; global policy Asia/Shanghai;
    student student-quota uses global for usage_date/tz.
    """
    dlg = TeacherCourseLlmDialog(course_id=1, session=None)
    dlg.set_course_quota_timezone_archive("UTC")


def test_t3_toggle_auto_grading_while_submissions_in_flight() -> None:
    """
    T3: Interleave: submissions while teacher disables auto_grading / is_enabled / endpoints.
    Assert stable error_code set (no quota_exceeded_course).
    """
    dlg = TeacherCourseLlmDialog(course_id=1, session=None)
    dlg.toggle_auto_grading_and_endpoints(False, [])
