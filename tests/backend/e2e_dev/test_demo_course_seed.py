"""Demo course seed data (teacher + students + homework)."""

from __future__ import annotations

from sqlalchemy import text

from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.demo_course_seed import seed_demo_course_bundle
from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import (
    Class,
    CourseExamWeight,
    CourseGradeScheme,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    CourseMaterial,
    CourseMaterialChapter,
    Homework,
    Student,
    Subject,
    User,
    UserRole,
)
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
    from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates

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
        t = db.query(User).filter(User.username == "teacher").first()
        assert t and "演示" in (t.real_name or "")
        for uname in ("stu1", "stu2", "stu3", "stu4", "stu5"):
            assert db.query(User).filter(User.username == uname).first()

        assert db.query(Student).filter(Student.student_no == "stu1").count() == 1

        course = db.query(Subject).filter(Subject.name == "数据挖掘").first()
        assert course is not None
        assert course.weekly_schedule
        assert course.description

        assert db.query(CourseGradeScheme).filter(CourseGradeScheme.subject_id == course.id).first() is not None
        exam_w = db.query(CourseExamWeight).filter(CourseExamWeight.subject_id == course.id).first()
        assert exam_w is not None
        assert exam_w.exam_type == "期末考试"

        st1 = db.query(Student).filter(Student.student_no == "stu1").first()
        assert st1 and st1.phone

        root = (
            db.query(CourseMaterialChapter)
            .filter(
                CourseMaterialChapter.subject_id == course.id,
                CourseMaterialChapter.title == "【演示】第一单元：导论与数据概览",
            )
            .first()
        )
        assert root is not None and root.parent_id is None
        mid = (
            db.query(CourseMaterialChapter)
            .filter(
                CourseMaterialChapter.subject_id == course.id,
                CourseMaterialChapter.parent_id == root.id,
                CourseMaterialChapter.title == "【演示】第一节：Python 环境与常用库",
            )
            .first()
        )
        assert mid is not None
        leaf = (
            db.query(CourseMaterialChapter)
            .filter(
                CourseMaterialChapter.subject_id == course.id,
                CourseMaterialChapter.parent_id == mid.id,
                CourseMaterialChapter.title == "【演示】1.1 课程资料与拓展阅读",
            )
            .first()
        )
        assert leaf is not None

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
        assert hw.reference_answer in (None, "")
        assert hw.max_submissions == 3
        assert hw.due_date is not None
        llm = db.query(Subject).filter(Subject.name == "大语言模型").first()
        assert llm is not None
        assert llm.course_type == "elective"
        assert db.query(CourseMaterial).filter(CourseMaterial.subject_id == llm.id).count() >= 1
        assert (
            db.query(Homework)
            .filter(Homework.subject_id == llm.id, Homework.title.contains("大语言模型"))
            .first()
        )
        req_cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == course.id).first()
        assert req_cfg is not None and req_cfg.is_enabled is True
        assert db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == req_cfg.id).count() >= 1
        el_cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == llm.id).first()
        assert el_cfg is not None
        assert el_cfg.is_enabled is False
        assert db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == el_cfg.id).count() >= 1
    finally:
        db.close()


def test_demo_seed_repairs_conflicting_stu1_username():
    """If username stu1 existed as non-student, seed fixes role and syncs password."""
    _reset_db()
    db = SessionLocal()
    try:
        klass = Class(name="人工智能1班", grade=2026)
        db.add(klass)
        db.flush()
        db.add(
            User(
                username="stu1",
                hashed_password=get_password_hash("wrong-pass"),
                real_name="Conflicting",
                role=UserRole.TEACHER.value,
                class_id=None,
                is_active=True,
            )
        )
        db.commit()
        seed_demo_course_bundle(db)
        stu = db.query(User).filter(User.username == "stu1").first()
        assert stu.role == UserRole.STUDENT.value
        assert stu.class_id == klass.id
    finally:
        db.close()

    client = TestClient(app)
    r = client.post("/api/auth/login", data={"username": "stu1", "password": "111111"})
    assert r.status_code == 200, r.text


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
