"""Homework grading creates in-app notifications for the matching student user."""

from __future__ import annotations

from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.llm_grading import process_grading_task
from app.main import app
from app.models import Homework, HomeworkGradingTask, Notification
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


def test_teacher_review_creates_student_notification(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    hid = ctx["homework_id"]
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=sh, json={"content": "hand in"}).json()
    sid = sub["id"]

    rv = client.put(
        f"/api/homeworks/{hid}/submissions/{sid}/review",
        headers=th,
        json={"review_score": 72, "review_comment": "不错"},
    )
    assert rv.status_code == 200

    notes = client.get("/api/notifications", headers=sh, params={"page": 1, "page_size": 20}).json()
    titles = [n["title"] for n in notes["data"]]
    assert any(t.startswith("作业已批改：") for t in titles)
    match = next(n for n in notes["data"] if n["title"].startswith("作业已批改："))
    assert "72" in (match.get("content") or "")
    assert "教师批改" in (match.get("content") or "")


def test_auto_grade_success_creates_student_notification(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    hid = ctx["homework_id"]
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    client.post(f"/api/homeworks/{hid}/submission", headers=sh, json={"content": "auto me"})

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch(
        "httpx.Client.post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(91.0, "auto ok")),
    ):
        process_grading_task(tid)

    notes = client.get("/api/notifications", headers=sh, params={"page": 1, "page_size": 20}).json()
    match = next((n for n in notes["data"] if n["title"].startswith("作业已批改：")), None)
    assert match is not None
    assert "91" in (match.get("content") or "")
    assert "自动评分" in (match.get("content") or "")


def test_teacher_review_idempotent_same_payload_one_notification(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    hid = ctx["homework_id"]
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sub = client.post(f"/api/homeworks/{hid}/submission", headers=sh, json={"content": "x"}).json()
    sid = sub["id"]
    body = {"review_score": 60.0, "review_comment": "same"}
    assert client.put(f"/api/homeworks/{hid}/submissions/{sid}/review", headers=th, json=body).status_code == 200
    assert client.put(f"/api/homeworks/{hid}/submissions/{sid}/review", headers=th, json=body).status_code == 200

    db = SessionLocal()
    try:
        hw = db.query(Homework).filter(Homework.id == hid).first()
        assert hw is not None
        count = (
            db.query(Notification)
            .filter(Notification.title == f"作业已批改：{hw.title}", Notification.class_id == hw.class_id)
            .count()
        )
        assert count == 1
    finally:
        db.close()
