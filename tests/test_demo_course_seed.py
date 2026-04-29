"""Demo course seed data (teacher + students + homework)."""

from __future__ import annotations

from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.demo_course_seed import seed_demo_course_bundle
from app.main import app
from app.models import Homework, Student, Subject, User
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


def test_demo_seed_creates_teacher_students_course_homework():
    _reset_db()
    db = SessionLocal()
    try:
        seed_demo_course_bundle(db)
        seed_demo_course_bundle(db)
    finally:
        db.close()

    db = SessionLocal()
    try:
        assert db.query(User).filter(User.username == "teacher").first()
        for uname in ("stu1", "stu2", "stu3", "stu4", "stu5"):
            assert db.query(User).filter(User.username == uname).first()

        assert db.query(Student).filter(Student.student_no == "stu1").count() == 1

        course = db.query(Subject).filter(Subject.name == "数据挖掘").first()
        assert course is not None
        hw = (
            db.query(Homework)
            .filter(
                Homework.subject_id == course.id,
                Homework.title.contains("数据挖掘第一次作业"),
            )
            .first()
        )
        assert hw is not None
        assert hw.max_score == 100
        assert hw.grade_precision == "integer"
        assert hw.auto_grading_enabled is True
        assert hw.response_language == "zh-CN"
        assert "Wine" in (hw.content or "")
        assert "宽松评分原则" in (hw.rubric_text or "")
    finally:
        db.close()


def test_demo_teacher_can_login():
    _reset_db()
    db = SessionLocal()
    try:
        seed_demo_course_bundle(db)
    finally:
        db.close()

    client = TestClient(app)
    r = client.post("/api/auth/login", data={"username": "teacher", "password": "111111"})
    assert r.status_code == 200, r.text
