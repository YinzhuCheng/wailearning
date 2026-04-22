"""Admin create/update: student role requires class_id."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, User, UserRole
from tests.llm_scenario import login_api


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
    ensure_admin()
    yield
    SessionLocal().close()


def ensure_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "adm").first():
            db.add(
                User(
                    username="adm",
                    hashed_password=get_password_hash("a"),
                    real_name="A",
                    role=UserRole.ADMIN.value,
                )
            )
            db.commit()
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_create_student_without_class_400(client: TestClient):
    h = login_api(client, "adm", "a")
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": "no_class_stu",
            "password": "p",
            "real_name": "N",
            "role": "student",
        },
    )
    assert r.status_code in (400, 422)


def test_create_student_with_class_200(client: TestClient):
    db = SessionLocal()
    try:
        k = Class(name="K1", grade=2026)
        db.add(k)
        db.commit()
        kid = k.id
    finally:
        db.close()
    h = login_api(client, "adm", "a")
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": "has_class_stu",
            "password": "p",
            "real_name": "H",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["class_id"] == kid
