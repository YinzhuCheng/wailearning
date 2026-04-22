"""
End-to-end style tests: student submission queues LLM grading; worker path is
exercised via process_grading_task with httpx mocked at _request_grade_from_endpoint.

See tests/conftest.py for env (SQLite, skip worker thread, skip retry backoff sleep).
"""

from __future__ import annotations

import uuid
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.llm_grading import process_grading_task
from app.main import app
from app.models import (
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    HomeworkGradingTask,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMEndpointPreset,
    LLMTokenUsageLog,
)
from tests.llm_scenario import ensure_admin, json_llm_response, login_api, make_grading_course_with_homework


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


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def grading_context(client: TestClient) -> dict:
    ensure_admin()
    ctx = make_grading_course_with_homework()
    ctx["client"] = client
    ctx["admin_headers"] = login_api(client, "pytest_admin", "pytest_admin_pass")
    ctx["teacher_headers"] = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    ctx["student_headers"] = login_api(client, ctx["student_username"], ctx["student_password"])
    return ctx


def test_submit_queues_task_and_retry_then_success_updates_submission(grading_context: dict):
    client: TestClient = grading_context["client"]
    hid = grading_context["homework_id"]
    student_h = grading_context["student_headers"]

    r = client.post(
        f"/api/homeworks/{hid}/submission",
        headers=student_h,
        json={"content": "My answer for pytest."},
    )
    assert r.status_code == 200, r.text
    sub_id = r.json()["id"]

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first()
        assert task is not None
        assert task.status == "queued"
        tid = task.id
    finally:
        db.close()

    responses = [
        httpx.Response(503, json={"error": "upstream"}),
        httpx.Response(200, json=json_llm_response(88.0, "auto comment")),
    ]

    def fake_post(self, url, **kwargs):
        return responses.pop(0)

    with mock.patch.object(httpx.Client, "post", fake_post):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "success"
        sub = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == sub_id).first()
        assert sub is not None
        assert sub.review_score == 88.0
        assert sub.review_comment == "auto comment"
        assert sub.latest_task_status == "success"
        auto = (
            db.query(HomeworkScoreCandidate)
            .filter(HomeworkScoreCandidate.attempt_id == sub.latest_attempt_id, HomeworkScoreCandidate.source == "auto")
            .first()
        )
        assert auto is not None
        assert auto.score == 88.0
    finally:
        db.close()


def test_auto_grading_disabled_no_task(grading_context: dict):
    ctx = make_grading_course_with_homework(auto_grading=False)
    client = grading_context["client"]
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])

    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "no auto grade"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        assert db.query(HomeworkGradingTask).count() == 0
    finally:
        db.close()


def test_course_llm_disabled_task_fails(grading_context: dict):
    ctx = make_grading_course_with_homework(course_llm_enabled=False)
    client = grading_context["client"]
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])

    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "answer"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first()
        assert task is not None
        tid = task.id
    finally:
        db.close()

    process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "failed"
        assert task.error_code == "llm_config_disabled"
    finally:
        db.close()


def test_non_retryable_http_fails_without_extra_llm_calls(grading_context: dict):
    ctx = make_grading_course_with_homework(preset_max_retries=0)
    client = grading_context["client"]
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])

    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "answer"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    calls: list[int] = []

    def fake_post(self, url, **kwargs):
        calls.append(1)
        return httpx.Response(401, json={"error": "bad key"})

    with mock.patch.object(httpx.Client, "post", fake_post):
        process_grading_task(tid)

    assert len(calls) == 1
    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "failed"
    finally:
        db.close()


def test_teacher_review_overrides_auto_score(grading_context: dict):
    client: TestClient = grading_context["client"]
    hid = grading_context["homework_id"]
    student_h = grading_context["student_headers"]
    teacher_h = grading_context["teacher_headers"]

    r = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "answer body"})
    assert r.status_code == 200, r.text
    sub_id = r.json()["id"]

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(70.0, "llm")),
    ):
        process_grading_task(tid)

    rev = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 92.0, "review_comment": "Adjusted by teacher"},
    )
    assert rev.status_code == 200, rev.text
    data = rev.json()
    assert data["review_score"] == 92.0
    assert data["review_comment"] == "Adjusted by teacher"

    db = SessionLocal()
    try:
        teachers = db.query(HomeworkScoreCandidate).filter(HomeworkScoreCandidate.source == "teacher").all()
        assert len(teachers) == 1
        assert teachers[0].score == 92.0
    finally:
        db.close()


def test_second_endpoint_used_when_first_keeps_retryable(grading_context: dict):
    """Two presets on the course; first returns 503 until exhausted; second succeeds."""
    base_ctx = make_grading_course_with_homework(preset_max_retries=0)
    uid = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        preset_b = LLMEndpointPreset(
            name=f"pytest-llm-preset-b-{uid}",
            base_url="https://api.virtual-b.test/v1/",
            api_key="sk-b",
            model_name="virtual-b",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(preset_b)
        db.flush()
        cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == base_ctx["subject_id"]).first()
        db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=preset_b.id, priority=2))
        db.commit()
        pid_b = preset_b.id
    finally:
        db.close()

    client: TestClient = grading_context["client"]
    student_h = login_api(client, base_ctx["student_username"], base_ctx["student_password"])

    r = client.post(
        f"/api/homeworks/{base_ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "multi endpoint"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    def fake_post(self, url, **kwargs):
        auth = (kwargs.get("headers") or {}).get("Authorization", "")
        if "sk-test" in auth:
            return httpx.Response(503, json={"error": "bad"})
        return httpx.Response(200, json=json_llm_response(81.0, "from B"))

    with mock.patch.object(httpx.Client, "post", fake_post):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "success"
        auto = (
            db.query(HomeworkScoreCandidate)
            .filter(HomeworkScoreCandidate.source == "auto")
            .order_by(HomeworkScoreCandidate.id.desc())
            .first()
        )
        assert auto.source_metadata.get("endpoint_id") == pid_b
    finally:
        db.close()


def test_quota_precheck_fails_without_llm_post(grading_context: dict):
    ctx = make_grading_course_with_homework(daily_student_token_limit=1)
    client = grading_context["client"]
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])

    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "quota block"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    calls: list[int] = []

    def fake_post(self, url, **kwargs):
        calls.append(1)
        return httpx.Response(200, json=json_llm_response(50.0, "should not"))

    with mock.patch.object(httpx.Client, "post", fake_post):
        process_grading_task(tid)

    assert calls == []
    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "failed"
        assert task.error_code == "quota_exceeded"
    finally:
        db.close()


def test_regrade_queues_new_task(grading_context: dict):
    client: TestClient = grading_context["client"]
    hid = grading_context["homework_id"]
    student_h = grading_context["student_headers"]
    teacher_h = grading_context["teacher_headers"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "v1"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    db = SessionLocal()
    try:
        first_tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(60.0, "first")),
    ):
        process_grading_task(first_tid)

    reg = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/regrade",
        headers=teacher_h,
        json={},
    )
    assert reg.status_code == 200, reg.text

    db = SessionLocal()
    try:
        tasks = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.asc()).all()
        assert len(tasks) == 2
        second = tasks[-1]
        assert second.status == "queued"
        second_id = second.id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(77.0, "regrade")),
    ):
        process_grading_task(second_id)

    db = SessionLocal()
    try:
        sub_row = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == sub_id).first()
        assert sub_row.review_score == 77.0
    finally:
        db.close()


def test_token_usage_recorded_after_success(grading_context: dict):
    client: TestClient = grading_context["client"]
    hid = grading_context["homework_id"]
    student_h = grading_context["student_headers"]

    r = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "token log test"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(50.0, "x")),
    ):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        log = db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == tid).first()
        assert log is not None
        assert log.total_tokens is not None
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.billed_total_tokens is not None
    finally:
        db.close()


def test_all_endpoints_exhausted_fails(grading_context: dict):
    """Single preset, max_retries=0: 503 and no more attempts → task fails."""
    ctx = make_grading_course_with_homework(preset_max_retries=0)
    client = grading_context["client"]
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])

    r = client.post(f"/api/homeworks/{ctx['homework_id']}/submission", headers=student_h, json={"content": "fail all"})
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(httpx.Client, "post", lambda self, url, **kwargs: httpx.Response(503, json={})):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "failed"
        assert "503" in (task.error_message or "") or "暂时不可用" in (task.error_message or "")
    finally:
        db.close()
