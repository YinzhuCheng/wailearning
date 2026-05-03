"""Admin POST /api/users/{id}/reset-password — default passwords and explicit override."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.db.database import SessionLocal
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import Class, User, UserRole


@pytest.fixture(autouse=True)
def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates

    ensure_schema_updates()
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "adm_rst").first():
            db.add(
                User(
                    username="adm_rst",
                    hashed_password=get_password_hash("admin-orig-9"),
                    real_name="Admin RST",
                    role=UserRole.ADMIN.value,
                )
            )
        if not db.query(User).filter(User.username == "tch_rst").first():
            db.add(
                User(
                    username="tch_rst",
                    hashed_password=get_password_hash("teacher-orig-9"),
                    real_name="Teacher RST",
                    role=UserRole.TEACHER.value,
                )
            )
        db.commit()
    finally:
        db.close()
    yield
    SessionLocal().close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": "adm_rst", "password": "admin-orig-9"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _teacher_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": "tch_rst", "password": "teacher-orig-9"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_admin_reset_student_password_defaults_to_student_no(client: TestClient):
    suf = uuid.uuid4().hex[:8]
    student_no = f"stu_rst_{suf}"
    db = SessionLocal()
    try:
        k = Class(name=f"RST班_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    h = _admin_headers(client)
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": student_no,
            "password": "old-student-secret-9",
            "real_name": "学生重置测",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    uid = r.json()["id"]

    r2 = client.post(f"/api/users/{uid}/reset-password", headers=h, json={})
    assert r2.status_code == 200, r2.text

    login = client.post("/api/auth/login", data={"username": student_no, "password": student_no})
    assert login.status_code == 200, login.text
    bad = client.post("/api/auth/login", data={"username": student_no, "password": "old-student-secret-9"})
    assert bad.status_code == 401


def test_admin_reset_teacher_roles_default_to_111111(client: TestClient):
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        k = Class(name=f"RST班CT_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        t = User(
            username=f"t_rst_{suf}",
            hashed_password=get_password_hash("old-t-9"),
            real_name="任课测",
            role=UserRole.TEACHER.value,
        )
        ct = User(
            username=f"ct_rst_{suf}",
            hashed_password=get_password_hash("old-ct-9"),
            real_name="班主任测",
            role=UserRole.CLASS_TEACHER.value,
            class_id=kid,
        )
        db.add_all([t, ct])
        db.commit()
        tid, ctid = t.id, ct.id
    finally:
        db.close()

    h = _admin_headers(client)
    assert client.post(f"/api/users/{tid}/reset-password", headers=h, json={}).status_code == 200
    assert client.post(f"/api/users/{ctid}/reset-password", headers=h, json={}).status_code == 200

    assert client.post("/api/auth/login", data={"username": f"t_rst_{suf}", "password": "111111"}).status_code == 200
    assert client.post("/api/auth/login", data={"username": f"ct_rst_{suf}", "password": "111111"}).status_code == 200


def test_admin_reset_password_explicit_overrides_default(client: TestClient):
    suf = uuid.uuid4().hex[:8]
    student_no = f"stu_exp_{suf}"
    db = SessionLocal()
    try:
        k = Class(name=f"RST班EXP_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    h = _admin_headers(client)
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": student_no,
            "password": "init-9chars",
            "real_name": "显式密码测",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    uid = r.json()["id"]

    explicit = "CustomPw!99"
    r2 = client.post(f"/api/users/{uid}/reset-password", headers=h, json={"new_password": explicit})
    assert r2.status_code == 200, r2.text

    assert client.post("/api/auth/login", data={"username": student_no, "password": explicit}).status_code == 200
    assert client.post("/api/auth/login", data={"username": student_no, "password": student_no}).status_code == 401


def test_non_admin_cannot_reset_user_password(client: TestClient):
    suf = uuid.uuid4().hex[:8]
    victim = f"stu_vic_{suf}"
    db = SessionLocal()
    try:
        k = Class(name=f"RST班V_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    ah = _admin_headers(client)
    r = client.post(
        "/api/users",
        headers=ah,
        json={
            "username": victim,
            "password": "vic-pass-9",
            "real_name": "受害者",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    vid = r.json()["id"]

    th = _teacher_headers(client)
    r403 = client.post(f"/api/users/{vid}/reset-password", headers=th, json={})
    assert r403.status_code == 403


def test_admin_reset_admin_requires_explicit_password(client: TestClient):
    db = SessionLocal()
    try:
        other = User(
            username="adm_other_rst",
            hashed_password=get_password_hash("other-adm-9"),
            real_name="副管",
            role=UserRole.ADMIN.value,
        )
        db.add(other)
        db.commit()
        oid = other.id
    finally:
        db.close()

    h = _admin_headers(client)
    r400 = client.post(f"/api/users/{oid}/reset-password", headers=h, json={})
    assert r400.status_code == 400

    new_p = "NewAdmPw!9"
    r_ok = client.post(f"/api/users/{oid}/reset-password", headers=h, json={"new_password": new_p})
    assert r_ok.status_code == 200, r_ok.text

    assert client.post("/api/auth/login", data={"username": "adm_other_rst", "password": new_p}).status_code == 200
