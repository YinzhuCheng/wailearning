"""Unit tests for LLM URL building, score JSON parsing, quota precheck, validate (mocked)."""

from __future__ import annotations

from unittest import mock

import httpx
import pytest
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.llm_grading import (
    _build_chat_completion_url,
    _parse_scoring_json,
    estimate_task_tokens,
    precheck_quota,
    validate_endpoint_connectivity,
)
from app.models import CourseLLMConfig, Homework


@pytest.fixture(autouse=True)
def _reset_db():
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            Base.metadata.drop_all(bind=conn)
            conn.execute(text("PRAGMA foreign_keys=ON"))
    else:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.bootstrap import ensure_schema_updates

    ensure_schema_updates()
    yield
    SessionLocal().close()


def test_build_chat_completion_url():
    assert _build_chat_completion_url("https://api.x/v1") == "https://api.x/v1/chat/completions"
    assert _build_chat_completion_url("https://api.x/v1/chat/completions") == "https://api.x/v1/chat/completions"
    assert _build_chat_completion_url("https://api.x/v1/chat/completions/") == "https://api.x/v1/chat/completions"


def test_parse_scoring_json_valid():
    hw = Homework(max_score=100, grade_precision="integer")
    out = _parse_scoring_json('{"score": 42, "comment": "ok"}', hw)
    assert out["score"] == 42.0
    assert out["comment"] == "ok"


def test_parse_scoring_json_markdown_fence():
    hw = Homework(max_score=10, grade_precision="integer")
    text = '```json\n{"score": 5, "comment": "c"}\n```'
    out = _parse_scoring_json(text, hw)
    assert out["score"] == 5.0


def test_parse_scoring_json_out_of_range():
    from app.llm_grading import RetryableLLMError

    hw = Homework(max_score=10, grade_precision="integer")
    with pytest.raises(RetryableLLMError) as exc:
        _parse_scoring_json('{"score": 99, "comment": "x"}', hw)
    assert "范围" in str(exc.value) or "超出" in str(exc.value)


def test_estimate_task_tokens():
    cfg = CourseLLMConfig(
        subject_id=1,
        estimated_chars_per_token=4.0,
        estimated_image_tokens=100,
        max_input_tokens=8000,
        max_output_tokens=500,
    )
    t = estimate_task_tokens(cfg, text_length=400, image_count=1)
    assert t > 500


def test_precheck_quota_allows_unlimited():
    db = SessionLocal()
    try:
        cfg = CourseLLMConfig(subject_id=1, is_enabled=True)
        ok, code = precheck_quota(db, cfg, student_id=1, subject_id=1, estimated_tokens=999_999_999)
        assert ok is True
        assert code is None
    finally:
        db.close()


def test_precheck_quota_blocks_student_when_mocked_usage_high():
    """precheck uses _get_used_tokens_for_scope; mock to force exceed without heavy DB."""
    db = SessionLocal()
    try:
        cfg = CourseLLMConfig(
            subject_id=1,
            is_enabled=True,
            daily_student_token_limit=100,
            quota_timezone="UTC",
        )
        with mock.patch("app.llm_grading._get_used_tokens_for_scope", return_value=95):
            ok, code = precheck_quota(db, cfg, student_id=1, subject_id=1, estimated_tokens=10)
        assert ok is False
        assert code == "quota_exceeded"
    finally:
        db.close()


def test_precheck_quota_blocks_course_when_mocked_usage_high():
    db = SessionLocal()
    try:
        cfg = CourseLLMConfig(
            subject_id=7,
            is_enabled=True,
            daily_course_token_limit=200,
            quota_timezone="UTC",
        )

        def _mock_used(db_inner, **kwargs):
            if kwargs.get("subject_id") == 7:
                return 195
            return 0

        with mock.patch("app.llm_grading._get_used_tokens_for_scope", side_effect=_mock_used):
            ok, code = precheck_quota(db, cfg, student_id=1, subject_id=7, estimated_tokens=10)
        assert ok is False
        assert code == "quota_exceeded"
    finally:
        db.close()


def test_validate_endpoint_connectivity_ok():
    def fake_post(self, url, **kwargs):
        return httpx.Response(200, json={"choices": [{"message": {"content": "  ok  "}}]})

    with mock.patch.object(httpx.Client, "post", fake_post):
        ok, msg = validate_endpoint_connectivity("https://x/v1", "k", "m", 5, 10)
    assert ok is True
    assert "通过" in msg


def test_validate_endpoint_connectivity_http_400():
    def fake_post(self, url, **kwargs):
        return httpx.Response(400, text="nope")

    with mock.patch.object(httpx.Client, "post", fake_post):
        ok, msg = validate_endpoint_connectivity("https://x/v1", "k", "m", 5, 10)
    assert ok is False
    assert "400" in msg
