"""Roster <-> user sync and safe queries when no accessible classes."""

from __future__ import annotations

from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, Student, User, UserRole
from app.student_user_sync import reconcile_student_users_and_roster
from fastapi.testclient import TestClient


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


def test_students_list_returns_empty_when_teacher_has_no_classes_not_500():
    """Previously Student.class_id.in_([]) caused SQL errors."""
    _reset_db()
    db = SessionLocal()
    try:
        c = Class(name="孤儿班", grade=2026)
        db.add(c)
        db.flush()
        db.add(
            Student(name="无名", student_no="orphan1", class_id=c.id),
        )
        u = User(
            username="solo_teacher",
            hashed_password=get_password_hash("pass"),
            real_name="Solo",
            role=UserRole.TEACHER.value,
        )
        db.add(u)
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    r = client.post(
        "/api/auth/login",
        data={"username": "solo_teacher", "password": "pass"},
    )
    assert r.status_code == 200, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    st = client.get("/api/students?page=1&page_size=20", headers=h)
    assert st.status_code == 200, st.text
    assert st.json()["total"] == 0


def test_reconcile_creates_user_from_roster_only():
    """Roster-first deployment: Student row gets matching User without manual load."""
    _reset_db()
    db = SessionLocal()
    try:
        c = Class(name="仅花名册班", grade=2026)
        db.add(c)
        db.flush()
        db.add(Student(name="仅花名册", student_no="roster_only_1", class_id=c.id))
        db.commit()
        reconcile_student_users_and_roster(db)
        db.commit()
        u = db.query(User).filter(User.username == "roster_only_1").first()
        assert u is not None
        assert u.role == UserRole.STUDENT.value
        assert u.class_id == c.id
    finally:
        db.close()
