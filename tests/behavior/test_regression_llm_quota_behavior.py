"""
R1–R3: Regression guards after removing course-level token caps.

Execution deferred — see tests/behavior/conftest.py.
"""


def test_r1_no_quota_exceeded_course_in_api_responses() -> None:
    """
    R1: Grep-level or contract test: student/teacher flows never surface quota_exceeded_course
    (grep fixture or forbidden substring in error_code JSON from homework submission APIs).
    """


def test_r2_course_llm_config_schema_no_removed_fields() -> None:
    """
    R2: GET /llm-settings/courses/{id} body lacks daily_course_token_limit / daily_student_token_limit;
    quota_usage only exposes agreed keys (usage_date, quota_timezone).
    """


def test_r3_orm_no_legacy_columns_postgres_migration() -> None:
    """
    R3: On PostgreSQL, information_schema confirms columns dropped (skip on SQLite weak mode).
    """
