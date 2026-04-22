"""
End-to-end style tests: student submission queues LLM grading; worker path is
exercised via process_grading_task with httpx mocked at _request_grade_from_endpoint.

See tests/conftest.py for env (SQLite, skip worker thread, skip retry backoff sleep).
"""

from __future__ import annotations

import json as json_stdlib
import uuid
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.llm_grading import process_grading_task
from app.main import app
from app.models import (
    Class,
    CourseEnrollment,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    HomeworkGradingTask,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMEndpointPreset,
    LLMTokenUsageLog,
    Student,
    Subject,
    User,
    UserRole,
)


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


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_grading_course_with_homework(
    *,
    auto_grading: bool = True,
    course_llm_enabled: bool = True,
    preset_max_retries: int = 2,
    daily_student_token_limit: int | None = None,
) -> dict:
    """Insert minimal rows for one course, validated LLM preset, config, and homework."""
    uid = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        klass = Class(name=f"pytest-class-{uid}", grade=2026)
        db.add(klass)
        db.flush()

        teacher = User(
            username=f"pytest_teacher_{uid}",
            hashed_password=get_password_hash("pytest_teacher_pass"),
            real_name="Pytest Teacher",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()

        stu_username = f"stu_{uid}"
        student_user = User(
            username=stu_username,
            hashed_password=get_password_hash("stu_pass"),
            real_name="Student One",
            role=UserRole.STUDENT.value,
            class_id=klass.id,
        )
        db.add(student_user)
        db.flush()

        stud = Student(name="Student One", student_no=stu_username, class_id=klass.id)
        db.add(stud)
        db.flush()

        course = Subject(name=f"pytest-course-{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()

        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=stud.id,
                class_id=klass.id,
                enrollment_type="required",
            )
        )

        preset = LLMEndpointPreset(
            name=f"pytest-llm-preset-{uid}",
            base_url="https://api.virtual.test/v1/",
            api_key="sk-test",
            model_name="virtual",
            max_retries=preset_max_retries,
            initial_backoff_seconds=1,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(preset)
        db.flush()

        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=course_llm_enabled,
            daily_student_token_limit=daily_student_token_limit,
            max_input_tokens=16000,
            max_output_tokens=1200,
            quota_timezone="UTC",
        )
        db.add(cfg)
        db.flush()
        db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=preset.id, priority=1))

        hw = Homework(
            title="pytest homework",
            content="Do the thing.",
            class_id=klass.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=auto_grading,
            created_by=teacher.id,
        )
        db.add(hw)
        db.commit()
        db.refresh(hw)
        db.refresh(preset)
        db.refresh(stud)
        db.refresh(teacher)
        return {
            "homework_id": hw.id,
            "preset_id": preset.id,
            "student_id": stud.id,
            "teacher_id": teacher.id,
            "subject_id": course.id,
            "student_username": stu_username,
            "student_password": "stu_pass",
            "teacher_username": teacher.username,
            "teacher_password": "pytest_teacher_pass",
        }
    finally:
        db.close()


@pytest.fixture
def grading_context(client: TestClient) -> dict:
    ctx = _make_grading_course_with_homework()
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "pytest_admin").first():
            db.add(
                User(
                    username="pytest_admin",
                    hashed_password=get_password_hash("pytest_admin_pass"),
                    real_name="Pytest Admin",
                    role=UserRole.ADMIN.value,
                )
            )
            db.commit()
    finally:
        db.close()
    ctx["client"] = client
    ctx["admin_headers"] = _login(client, "pytest_admin", "pytest_admin_pass")
    ctx["teacher_headers"] = _login(client, ctx["teacher_username"], ctx["teacher_password"])
    ctx["student_headers"] = _login(client, ctx["student_username"], ctx["student_password"])
    return ctx


def _json_llm_response(score: float, comment: str) -> dict:
    payload = json_stdlib.dumps({"score": score, "comment": comment}, ensure_ascii=False)
    return {
        "choices": [{"message": {"content": payload}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


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
        httpx.Response(200, json=_json_llm_response(88.0, "auto comment")),
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
    ctx = _make_grading_course_with_homework(auto_grading=False)
    client = grading_context["client"]
    student_h = _login(client, ctx["student_username"], ctx["student_password"])

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
    ctx = _make_grading_course_with_homework(course_llm_enabled=False)
    client = grading_context["client"]
    student_h = _login(client, ctx["student_username"], ctx["student_password"])

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
    ctx = _make_grading_course_with_homework(preset_max_retries=0)
    client = grading_context["client"]
    student_h = _login(client, ctx["student_username"], ctx["student_password"])

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
        lambda self, url, **kwargs: httpx.Response(200, json=_json_llm_response(70.0, "llm")),
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
    base_ctx = _make_grading_course_with_homework(preset_max_retries=0)
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
    student_h = _login(client, base_ctx["student_username"], base_ctx["student_password"])

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
        return httpx.Response(200, json=_json_llm_response(81.0, "from B"))

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
    ctx = _make_grading_course_with_homework(daily_student_token_limit=1)
    client = grading_context["client"]
    student_h = _login(client, ctx["student_username"], ctx["student_password"])

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
        return httpx.Response(200, json=_json_llm_response(50.0, "should not"))

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
        lambda self, url, **kwargs: httpx.Response(200, json=_json_llm_response(60.0, "first")),
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
        lambda self, url, **kwargs: httpx.Response(200, json=_json_llm_response(77.0, "regrade")),
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
        lambda self, url, **kwargs: httpx.Response(200, json=_json_llm_response(50.0, "x")),
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
    ctx = _make_grading_course_with_homework(preset_max_retries=0)
    client = grading_context["client"]
    student_h = _login(client, ctx["student_username"], ctx["student_password"])

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
