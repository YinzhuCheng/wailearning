"""Course score composition, grade scheme, and score appeals API."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import HomeworkScoreCandidate, HomeworkSubmission
from apps.backend.wailearning_backend.domains.scores.composition import (
    OTHER_DAILY_EXAM_TYPE,
)
from tests.scenarios.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


@pytest.fixture(autouse=True)
def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates

    ensure_schema_updates()
    yield
    SessionLocal().close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _set_homework_score(db, homework_id: int, student_id: int, teacher_id: int, score: float):
    sub = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.homework_id == homework_id, HomeworkSubmission.student_id == student_id)
        .first()
    )
    assert sub and sub.latest_attempt_id
    db.add(
        HomeworkScoreCandidate(
            attempt_id=sub.latest_attempt_id,
            homework_id=homework_id,
            student_id=student_id,
            source="teacher",
            score=score,
            created_by=teacher_id,
        )
    )
    sub.review_score = score
    db.commit()


def test_grade_scheme_and_weights_must_sum_to_100(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sid = ctx["subject_id"]

    r = client.put(f"/api/scores/grade-scheme/{sid}", headers=th, json={"homework_weight": 30, "extra_daily_weight": 20})
    assert r.status_code == 200, r.text

    bad = client.put(
        f"/api/scores/weights/{sid}",
        headers=th,
        json={"items": [{"exam_type": "期中", "weight": 60}]},
    )
    assert bad.status_code == 400

    ok = client.put(
        f"/api/scores/weights/{sid}",
        headers=th,
        json={"items": [{"exam_type": "期中", "weight": 50}]},
    )
    assert ok.status_code == 200, ok.text


def test_composition_and_student_appeal(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    sid = ctx["subject_id"]
    hid = ctx["homework_id"]
    cid = ctx["class_id"]
    sem = "2026-春季"

    client.put(f"/api/scores/grade-scheme/{sid}", headers=th, json={"homework_weight": 30, "extra_daily_weight": 20})
    client.put(
        f"/api/scores/weights/{sid}",
        headers=th,
        json={"items": [{"exam_type": "期末", "weight": 50}]},
    )

    assert client.post(f"/api/homeworks/{hid}/submission", headers=sh, json={"content": "hw"}).status_code == 200
    db = SessionLocal()
    try:
        _set_homework_score(db, hid, ctx["student_id"], ctx["teacher_id"], 80.0)
    finally:
        db.close()

    r_other = client.post(
        "/api/scores",
        headers=th,
        json={
            "student_id": ctx["student_id"],
            "subject_id": sid,
            "class_id": cid,
            "score": 90,
            "exam_type": OTHER_DAILY_EXAM_TYPE,
            "semester": sem,
        },
    )
    assert r_other.status_code == 200, r_other.text

    r_exam = client.post(
        "/api/scores",
        headers=th,
        json={
            "student_id": ctx["student_id"],
            "subject_id": sid,
            "class_id": cid,
            "score": 70,
            "exam_type": "期末",
            "semester": sem,
        },
    )
    assert r_exam.status_code == 200, r_exam.text

    comp = client.get(
        "/api/scores/composition/me",
        headers=sh,
        params={"subject_id": sid, "semester": sem},
    )
    assert comp.status_code == 200, comp.text
    body = comp.json()
    assert body["homework_average_percent"] == 80.0
    assert body["other_daily_score"] == 90.0
    assert body["exam_scores"].get("期末") == 70.0
    assert body["weighted_total"] is not None
    assert abs(body["weighted_total"] - 77.0) < 0.01

    ap = client.post(
        f"/api/scores/appeals?subject_id={sid}",
        headers=sh,
        json={"semester": sem, "target_component": "total", "reason_text": "总分有疑问"},
    )
    assert ap.status_code == 200, ap.text

    lst = client.get("/api/scores/appeals", headers=th, params={"subject_id": sid})
    assert lst.status_code == 200
    assert len(lst.json()) >= 1

    aid = lst.json()[0]["id"]
    up = client.put(
        f"/api/scores/appeals/{aid}",
        headers=th,
        json={"teacher_response": "已复核，成绩无误。", "status": "resolved"},
    )
    assert up.status_code == 200, up.text
    assert up.json()["status"] == "resolved"


def test_duplicate_pending_appeal_rejected(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    sid = ctx["subject_id"]
    sem = "2026-春季"

    client.put(f"/api/scores/grade-scheme/{sid}", headers=th, json={"homework_weight": 30, "extra_daily_weight": 20})
    client.put(
        f"/api/scores/weights/{sid}",
        headers=th,
        json={"items": [{"exam_type": "期末", "weight": 50}]},
    )

    p1 = client.post(
        f"/api/scores/appeals?subject_id={sid}",
        headers=sh,
        json={"semester": sem, "target_component": "total", "reason_text": "第一次"},
    )
    assert p1.status_code == 200, p1.text
    p2 = client.post(
        f"/api/scores/appeals?subject_id={sid}",
        headers=sh,
        json={"semester": sem, "target_component": "total", "reason_text": "第二次"},
    )
    assert p2.status_code == 400


def test_appeal_response_invalid_status(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    sh = login_api(client, ctx["student_username"], ctx["student_password"])
    sid = ctx["subject_id"]
    sem = "2026-春季"

    client.put(f"/api/scores/grade-scheme/{sid}", headers=th, json={"homework_weight": 30, "extra_daily_weight": 20})
    client.put(
        f"/api/scores/weights/{sid}",
        headers=th,
        json={"items": [{"exam_type": "期末", "weight": 50}]},
    )

    ap = client.post(
        f"/api/scores/appeals?subject_id={sid}",
        headers=sh,
        json={"semester": sem, "target_component": "homework_avg", "reason_text": "作业分"},
    )
    assert ap.status_code == 200, ap.text
    aid = ap.json()["id"]

    bad = client.put(
        f"/api/scores/appeals/{aid}",
        headers=th,
        json={"teacher_response": "说明", "status": "not_a_status"},
    )
    assert bad.status_code == 400

