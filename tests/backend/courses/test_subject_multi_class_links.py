"""Regression tests for ``subject_class_links`` (multi-class required courses + elective decoupling)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates, seed_default_system_settings
from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.db.database import SessionLocal
from apps.backend.wailearning_backend.db.models import Class, CourseEnrollment, Student, Subject, SubjectClassLink, User, UserRole
from apps.backend.wailearning_backend.main import app


@pytest.fixture(autouse=True)
def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    ensure_schema_updates()
    db = SessionLocal()
    try:
        seed_default_system_settings(db)
    finally:
        db.close()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return _headers(r.json()["access_token"])


def _seed_admin(username: str, password: str) -> None:
    db = SessionLocal()
    try:
        db.add(
            User(
                username=username,
                hashed_password=get_password_hash(password),
                real_name=username,
                role=UserRole.ADMIN.value,
            )
        )
        db.commit()
    finally:
        db.close()


def test_required_course_two_classes_auto_enrolls_each_class_roster(client: TestClient):
    suffix = uuid.uuid4().hex[:10]
    admin_user = f"adm_mc_{suffix}"
    _seed_admin(admin_user, "pw123456")
    h = _login(client, admin_user, "pw123456")

    c1 = client.post("/api/classes", headers=h, json={"name": f"A-{suffix}", "grade": 1})
    assert c1.status_code == 200, c1.text
    id1 = c1.json()["id"]
    c2 = client.post("/api/classes", headers=h, json={"name": f"B-{suffix}", "grade": 1})
    assert c2.status_code == 200, c2.text
    id2 = c2.json()["id"]

    for cid, no in ((id1, "s1"), (id2, "s2")):
        r = client.post(
            "/api/students",
            headers=h,
            json={"name": f"stu-{no}", "student_no": no, "gender": "male", "class_id": cid},
        )
        assert r.status_code == 200, r.text

    title = f"Math-{suffix}"
    created = client.post(
        "/api/subjects",
        headers=h,
        json={
            "name": title,
            "course_type": "required",
            "status": "active",
            "class_links": [
                {"class_id": id1, "enrollment_mode": "all_in_class"},
                {"class_id": id2, "enrollment_mode": "all_in_class"},
            ],
            "course_times": [],
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    links = created.json().get("class_links") or []
    assert len(links) == 2

    db = SessionLocal()
    try:
        subs = db.query(Student).filter(Student.student_no.in_(["s1", "s2"])).all()
        assert len(subs) == 2
        enroll_rows = db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == subject_id).all()
        assert len(enroll_rows) == 2
        class_ids = {e.class_id for e in enroll_rows}
        assert class_ids == {id1, id2}
    finally:
        db.close()


def test_elective_create_rejects_class_binding(client: TestClient):
    suffix = uuid.uuid4().hex[:10]
    admin_user = f"adm_el_{suffix}"
    _seed_admin(admin_user, "pw123456")
    h = _login(client, admin_user, "pw123456")

    c1 = client.post("/api/classes", headers=h, json={"name": f"C-{suffix}", "grade": 1})
    assert c1.status_code == 200, c1.text
    cid = c1.json()["id"]

    bad = client.post(
        "/api/subjects",
        headers=h,
        json={
            "name": f"Elective-{suffix}",
            "course_type": "elective",
            "status": "active",
            "class_id": cid,
            "course_times": [],
        },
    )
    assert bad.status_code == 400


def test_roster_subset_link_does_not_auto_sync_whole_class(client: TestClient):
    suffix = uuid.uuid4().hex[:10]
    admin_user = f"adm_rs_{suffix}"
    _seed_admin(admin_user, "pw123456")
    h = _login(client, admin_user, "pw123456")

    c1 = client.post("/api/classes", headers=h, json={"name": f"D-{suffix}", "grade": 1})
    assert c1.status_code == 200, c1.text
    cid = c1.json()["id"]

    r = client.post(
        "/api/students",
        headers=h,
        json={"name": "solo", "student_no": "solo1", "gender": "male", "class_id": cid},
    )
    assert r.status_code == 200, r.text

    title = f"Physics-{suffix}"
    created = client.post(
        "/api/subjects",
        headers=h,
        json={
            "name": title,
            "course_type": "required",
            "status": "active",
            "class_links": [{"class_id": cid, "enrollment_mode": "roster_subset"}],
            "course_times": [],
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]

    db = SessionLocal()
    try:
        cnt = db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == subject_id).count()
        assert cnt == 0
        row = db.query(SubjectClassLink).filter(SubjectClassLink.subject_id == subject_id).first()
        assert row is not None
        assert row.enrollment_mode == "roster_subset"
    finally:
        db.close()
