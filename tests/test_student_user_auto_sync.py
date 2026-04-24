"""Automatic sync between Student roster and User student accounts."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, Gender, Student, User, UserRole


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
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "adm").first():
            db.add(
                User(
                    username="adm",
                    hashed_password=get_password_hash("a"),
                    real_name="Admin",
                    role=UserRole.ADMIN.value,
                )
            )
            db.commit()
    finally:
        db.close()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": "adm", "password": "a"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_post_student_creates_matching_user(client: TestClient):
    db = SessionLocal()
    try:
        k = Class(name="自动班A", grade=2026)
        db.add(k)
        db.commit()
        kid = k.id
    finally:
        db.close()

    ah = _admin_headers(client)
    r = client.post(
        "/api/students",
        headers=ah,
        json={
            "name": "张三",
            "student_no": "auto_sn_1",
            "gender": "male",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == "auto_sn_1").first()
        assert u is not None
        assert u.role == UserRole.STUDENT.value
        assert u.class_id == kid
        assert u.real_name == "张三"
    finally:
        db.close()


def test_post_user_student_creates_roster_row(client: TestClient):
    db = SessionLocal()
    try:
        k = Class(name="自动班B", grade=2026)
        db.add(k)
        db.commit()
        kid = k.id
    finally:
        db.close()

    ah = _admin_headers(client)
    r = client.post(
        "/api/users",
        headers=ah,
        json={
            "username": "auto_sn_2",
            "password": "secret12",
            "real_name": "李四",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.student_no == "auto_sn_2", Student.class_id == kid).first()
        assert st is not None
        assert st.name == "李四"
    finally:
        db.close()


def test_update_student_no_rekeys_user_username(client: TestClient):
    db = SessionLocal()
    try:
        k = Class(name="自动班C", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        st = Student(name="王五", student_no="old_no", gender=Gender.MALE, class_id=kid)
        db.add(st)
        db.flush()
        sid = st.id
        u = User(
            username="old_no",
            hashed_password=get_password_hash("x"),
            real_name="王五",
            role=UserRole.STUDENT.value,
            class_id=kid,
        )
        db.add(u)
        db.commit()
    finally:
        db.close()

    ah = _admin_headers(client)
    r = client.put(
        f"/api/students/{sid}",
        headers=ah,
        json={"student_no": "new_no"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == "new_no").first()
        assert u is not None
        assert db.query(User).filter(User.username == "old_no").first() is None
        st = db.query(Student).filter(Student.id == sid).first()
        assert st.student_no == "new_no"
    finally:
        db.close()
