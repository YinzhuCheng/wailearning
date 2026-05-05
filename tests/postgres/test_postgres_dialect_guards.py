"""Twenty PostgreSQL-specific or Postgres-revealing guards (skip on SQLite).

These complement default SQLite runs: concurrency, information_schema, and type checks
that differ from SQLite. Requires ``TEST_DATABASE_URL`` for PostgreSQL.
"""

from __future__ import annotations

import threading
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.db.database import SessionLocal, engine
from apps.backend.wailearning_backend.db.models import (
    Class,
    CourseEnrollment,
    Gender,
    Student,
    Subject,
    User,
    UserRole,
)
from apps.backend.wailearning_backend.main import app
from tests.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework

pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="Set TEST_DATABASE_URL to a PostgreSQL URL to run dialect guard tests",
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_pg01_engine_reports_postgresql():
    assert engine.dialect.name == "postgresql"


def test_pg02_server_version_selectable():
    db = SessionLocal()
    try:
        ver = db.execute(text("SELECT version()")).scalar_one()
        assert "PostgreSQL" in ver
    finally:
        db.close()


def test_pg03_information_schema_course_llm_configs_no_legacy_token_columns():
    db = SessionLocal()
    try:
        rows = db.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'course_llm_configs'
                  AND column_name IN (
                      'daily_course_token_limit',
                      'daily_student_token_limit',
                      'quota_timezone',
                      'estimated_chars_per_token',
                      'estimated_image_tokens'
                  )
                """
            )
        ).fetchall()
        assert rows == []
    finally:
        db.close()


def test_pg04_homework_attempts_prior_attempt_fk_column_exists():
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'homework_attempts'
                  AND column_name = 'prior_attempt_id'
                """
            )
        ).fetchone()
        assert row is not None
        assert row[0] in ("integer", "bigint")
    finally:
        db.close()


def test_pg05_course_discussion_entries_created_at_is_timestamptz():
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'course_discussion_entries'
                  AND column_name = 'created_at'
                """
            )
        ).fetchone()
        assert row is not None
        assert "timestamp" in row[0].lower()
    finally:
        db.close()


def test_pg06_duplicate_course_enrollment_raises_integrity_error():
    uid = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        k = Class(name=f"pg_dup_class_{uid}", grade=2026)
        db.add(k)
        db.flush()
        t = User(
            username=f"pg_teach_{uid}",
            hashed_password=get_password_hash("pw"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(t)
        db.flush()
        st = Student(name="S", student_no=f"pg_stu_{uid}", gender=Gender.MALE, class_id=k.id)
        db.add(st)
        db.flush()
        sub = Subject(name=f"pg_sub_{uid}", teacher_id=t.id, class_id=k.id, course_type="required", status="active")
        db.add(sub)
        db.flush()
        e = CourseEnrollment(
            subject_id=sub.id,
            student_id=st.id,
            class_id=k.id,
            enrollment_type="required",
            can_remove=False,
        )
        db.add(e)
        db.commit()

        db.add(
            CourseEnrollment(
                subject_id=sub.id,
                student_id=st.id,
                class_id=k.id,
                enrollment_type="required",
                can_remove=False,
            )
        )
        with pytest.raises(IntegrityError):
            try:
                db.commit()
            finally:
                db.rollback()
    finally:
        db.close()


def test_pg07_returning_clause_returns_inserted_id():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        rid = db.execute(
            text("INSERT INTO classes (name, grade) VALUES (:n, :g) RETURNING id"),
            {"n": f"pg_ret_{uid}", "g": 2026},
        ).scalar_one()
        assert isinstance(rid, int)
        db.commit()
    finally:
        db.close()


def test_pg08_uncommitted_insert_not_visible_in_other_session():
    uid = uuid.uuid4().hex[:8]
    barrier = threading.Barrier(2)
    visible: dict[str, bool] = {"ok": False}

    def writer():
        dbw = SessionLocal()
        try:
            dbw.execute(
                text("INSERT INTO classes (name, grade) VALUES (:n, :g)"),
                {"n": f"pg_tx_{uid}", "g": 2026},
            )
            barrier.wait()
            import time

            time.sleep(0.15)
            dbw.commit()
        finally:
            dbw.close()

    def reader():
        dbr = SessionLocal()
        try:
            barrier.wait()
            cnt = dbr.execute(
                text("SELECT COUNT(*) FROM classes WHERE name = :n"),
                {"n": f"pg_tx_{uid}"},
            ).scalar_one()
            visible["ok"] = cnt == 0
        finally:
            dbr.close()

    tw = threading.Thread(target=writer)
    tr = threading.Thread(target=reader)
    tw.start()
    tr.start()
    tw.join()
    tr.join()
    assert visible["ok"] is True


def test_pg09_json_agg_homework_ids_empty():
    db = SessionLocal()
    try:
        raw = db.execute(text("SELECT COALESCE(json_agg(id), '[]'::json)::text FROM homeworks WHERE id < 0")).scalar_one()
        assert raw == "[]"
    finally:
        db.close()


def test_pg10_boolean_true_literal():
    db = SessionLocal()
    try:
        assert db.execute(text("SELECT true::boolean")).scalar_one() is True
    finally:
        db.close()


def test_pg11_auth_login_after_seed(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    r = client.post(
        "/api/auth/login",
        data={"username": ctx["student_username"], "password": ctx["student_password"]},
    )
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_pg12_dashboard_stats_requires_auth(client: TestClient):
    r = client.get("/api/dashboard/stats")
    assert r.status_code == 401


def test_pg13_dashboard_stats_teacher_ok(client: TestClient):
    ctx = make_grading_course_with_homework()
    h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    r = client.get("/api/dashboard/stats", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert "total_students" in body


def test_pg14_notifications_page_size_boundary_422(client: TestClient):
    ctx = make_grading_course_with_homework()
    h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.get("/api/notifications?page=1&page_size=200", headers=h)
    assert r.status_code == 422


def test_pg15_notifications_page_size_boundary_ok(client: TestClient):
    ctx = make_grading_course_with_homework()
    h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.get("/api/notifications?page=1&page_size=100", headers=h)
    assert r.status_code == 200


def test_pg16_discussion_post_and_list_order(client: TestClient):
    ctx = make_grading_course_with_homework()
    st = login_api(client, ctx["student_username"], ctx["student_password"])
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    base = {
        "target_type": "homework",
        "target_id": ctx["homework_id"],
        "subject_id": ctx["subject_id"],
        "class_id": ctx["class_id"],
        "body": "pg_line_a",
    }
    assert client.post("/api/discussions", headers=st, json=base).status_code == 200
    base["body"] = "pg_line_b"
    assert client.post("/api/discussions", headers=st, json=base).status_code == 200
    r = client.get(
        "/api/discussions",
        headers=th,
        params={
            "target_type": "homework",
            "target_id": ctx["homework_id"],
            "subject_id": ctx["subject_id"],
            "class_id": ctx["class_id"],
            "page": 1,
            "page_size": 50,
        },
    )
    assert r.status_code == 200
    data = r.json()["data"]
    keys = [(row["created_at"], row["id"]) for row in data]
    assert keys == sorted(keys)


def test_pg17_settings_public_unauthenticated(client: TestClient):
    r = client.get("/api/settings/public")
    assert r.status_code == 200


def test_pg18_health_endpoint(client: TestClient):
    r = client.get("/api/health")
    assert r.status_code == 200


def test_pg19_semesters_list_authenticated(client: TestClient):
    ensure_admin()
    h = login_api(client, "pytest_admin", "pytest_admin_pass")
    r = client.get("/api/semesters", headers=h)
    assert r.status_code == 200


def test_pg20_classes_list_teacher(client: TestClient):
    ctx = make_grading_course_with_homework()
    h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    r = client.get("/api/classes", headers=h)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
