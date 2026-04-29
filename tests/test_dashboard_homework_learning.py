"""Dashboard homework learning analytics: trend and resubmission lift."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Homework, HomeworkScoreCandidate, HomeworkSubmission, Subject
from tests.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


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


def test_homework_learning_requires_subject_id(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    r = client.get("/api/dashboard/analysis/homework-learning", headers=th)
    assert r.status_code == 400
    assert "subject_id" in (r.json().get("detail") or "").lower() or "subject_id" in str(r.json())


def test_homework_learning_trend_two_homeworks(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    sid = ctx["subject_id"]
    hid1 = ctx["homework_id"]

    db = SessionLocal()
    try:
        course = db.query(Subject).filter(Subject.id == sid).first()
        hw2 = Homework(
            title="Second HW",
            content="x",
            class_id=course.class_id,
            subject_id=sid,
            max_score=100,
            auto_grading_enabled=False,
            created_by=ctx["teacher_id"],
            due_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        db.add(hw2)
        db.commit()
        db.refresh(hw2)
        hid2 = hw2.id
    finally:
        db.close()

    # Submissions
    assert client.post(f"/api/homeworks/{hid1}/submission", headers=sh, json={"content": "s1"}).status_code == 200
    assert client.post(f"/api/homeworks/{hid2}/submission", headers=sh, json={"content": "s2"}).status_code == 200

    db = SessionLocal()
    try:
        sub1 = (
            db.query(HomeworkSubmission)
            .filter(HomeworkSubmission.homework_id == hid1, HomeworkSubmission.student_id == ctx["student_id"])
            .first()
        )
        sub2 = (
            db.query(HomeworkSubmission)
            .filter(HomeworkSubmission.homework_id == hid2, HomeworkSubmission.student_id == ctx["student_id"])
            .first()
        )
        assert sub1 and sub2
        att1 = sub1.latest_attempt
        att2 = sub2.latest_attempt
        assert att1 and att2
        db.add_all(
            [
                HomeworkScoreCandidate(
                    attempt_id=att1.id,
                    homework_id=hid1,
                    student_id=ctx["student_id"],
                    source="teacher",
                    score=70.0,
                    created_by=ctx["teacher_id"],
                ),
                HomeworkScoreCandidate(
                    attempt_id=att2.id,
                    homework_id=hid2,
                    student_id=ctx["student_id"],
                    source="teacher",
                    score=90.0,
                    created_by=ctx["teacher_id"],
                ),
            ]
        )
        sub1.review_score = 70.0
        sub2.review_score = 90.0
        db.commit()
    finally:
        db.close()

    r = client.get("/api/dashboard/analysis/homework-learning", headers=th, params={"subject_id": sid})
    assert r.status_code == 200, r.text
    body = r.json()
    trend = body["homework_trend"]
    assert len(trend) == 2
    titles = [row["title"] for row in trend]
    assert "pytest homework" in titles and "Second HW" in titles
    by_title = {row["title"]: row for row in trend}
    assert by_title["pytest homework"]["avg_score"] == 70.0
    assert by_title["Second HW"]["avg_score"] == 90.0
    assert body["resubmit_lift"] == []


def test_homework_learning_resubmit_lift(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    hid = ctx["homework_id"]

    db = SessionLocal()
    try:
        hw = db.query(Homework).filter(Homework.id == hid).first()
        hw.max_submissions = 3
        db.commit()
    finally:
        db.close()

    assert client.post(f"/api/homeworks/{hid}/submission", headers=sh, json={"content": "a1"}).status_code == 200
    assert client.post(f"/api/homeworks/{hid}/submission", headers=sh, json={"content": "a2"}).status_code == 200

    r_me = client.get(f"/api/homeworks/{hid}/submission/me", headers=sh)
    assert r_me.status_code == 200, r_me.text
    submission_id = r_me.json()["id"]

    db = SessionLocal()
    try:
        sub = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == submission_id).first()
        attempts = sorted(sub.attempts, key=lambda a: (a.submitted_at, a.id))
        assert len(attempts) == 2
        aid_first, aid_last = attempts[0].id, attempts[1].id
    finally:
        db.close()

    rv1 = client.put(
        f"/api/homeworks/{hid}/submissions/{submission_id}/review",
        headers=th,
        json={"attempt_id": aid_first, "review_score": 50, "review_comment": "first"},
    )
    assert rv1.status_code == 200, rv1.text
    rv2 = client.put(
        f"/api/homeworks/{hid}/submissions/{submission_id}/review",
        headers=th,
        json={"attempt_id": aid_last, "review_score": 80, "review_comment": "last"},
    )
    assert rv2.status_code == 200, rv2.text

    r = client.get(
        "/api/dashboard/analysis/homework-learning",
        headers=th,
        params={"subject_id": ctx["subject_id"]},
    )
    assert r.status_code == 200, r.text
    lift = r.json()["resubmit_lift"]
    assert len(lift) == 1
    assert lift[0]["homework_id"] == hid
    assert lift[0]["student_count"] == 1
    assert lift[0]["avg_first_score"] == 50.0
    assert lift[0]["avg_last_score"] == 80.0
    assert lift[0]["avg_lift"] == 30.0
