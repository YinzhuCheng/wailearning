"""
A1–A5: Admin global LLM policy (daily cap, timezone, max_parallel_grading_tasks, bulk overrides).

Execution deferred — see tests/behavior/conftest.py (collection hook skips this package).
"""

from __future__ import annotations

from typing import Any


class AdminLlmPolicyPage:
    """Playwright page object placeholder (next round)."""

    def __init__(self, base_url: str, session: Any) -> None:
        self._base_url = base_url
        self._session = session

    def open_settings_llm_section(self) -> None:
        """Navigate: login as admin → Settings → LLM 用量与额度 card."""

    def read_displayed_defaults(self) -> dict[str, Any]:
        """Return UI snapshot: default_daily_student_tokens, quota_timezone, max_parallel."""
        return {}

    def set_default_daily_tokens(self, value: int) -> None:
        """Change 默认每人每日 token → save."""

    def set_quota_timezone(self, tz: str) -> None:
        """Change 额度统计时区 → save."""

    def set_max_parallel_grading_tasks(self, n: int) -> None:
        """Change 并发评分任务数 → save."""

    def apply_bulk_override(
        self,
        *,
        scope: str,
        class_id: int | None,
        subject_id: int | None,
        daily_tokens: int | None,
        clear_override: bool,
    ) -> None:
        """Submit bulk override form."""


def test_a1_first_open_settings_shows_policy_defaults(behavior_base_url: str) -> None:
    """
    A1: Admin opens Settings → LLM block loads with 100k / Asia/Shanghai / 3 parallel.
    Cross-check: GET /api/llm-settings/admin/quota-policy matches UI.
    """
    page = AdminLlmPolicyPage(behavior_base_url, session=None)
    page.open_settings_llm_section()
    page.read_displayed_defaults()


def test_a2_change_default_student_cap_refreshes_student_card(behavior_base_url: str) -> None:
    """
    A2: Admin lowers/raises default cap → student session (My Courses) shows new
    daily_student_token_limit + global_default alignment when no override.
    """
    page = AdminLlmPolicyPage(behavior_base_url, session=None)
    page.set_default_daily_tokens(50_000)


def test_a3_timezone_flip_changes_usage_date_boundary(behavior_base_url: str) -> None:
    """
    A3: Toggle global quota_timezone near calendar boundary; student quota usage_date shifts.
    Precondition: optional time freeze or controlled clock (next round).
    """
    page = AdminLlmPolicyPage(behavior_base_url, session=None)
    page.set_quota_timezone("UTC")
    page.set_quota_timezone("Asia/Shanghai")


def test_a4_parallel_cap_change_with_queue_backlog(behavior_base_url: str) -> None:
    """
    A4: Seed N queued grading tasks → set parallel=3 → observe ≤3 processing;
    then set parallel=1 → next wave obeys cap.
    """
    page = AdminLlmPolicyPage(behavior_base_url, session=None)
    page.set_max_parallel_grading_tasks(3)
    page.set_max_parallel_grading_tasks(1)


def test_a5_bulk_override_then_clear(behavior_base_url: str) -> None:
    """
    A5: Bulk scope class/subject/all → verify LLMStudentTokenOverride rows;
    clear_override → rows removed; student API uses_personal_override flips.
    """
    page = AdminLlmPolicyPage(behavior_base_url, session=None)
    page.apply_bulk_override(scope="class", class_id=1, subject_id=None, daily_tokens=77_777, clear_override=False)
    page.apply_bulk_override(scope="class", class_id=1, subject_id=None, daily_tokens=None, clear_override=True)
