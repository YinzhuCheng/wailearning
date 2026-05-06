"""Demo course seed data (teacher + students + homework)."""

from __future__ import annotations

from sqlalchemy import text

from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.domains.seed.demo import seed_demo_course_bundle
from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import (
    Class,
    CourseEnrollment,
    CourseExamWeight,
    CourseGradeScheme,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    CourseMaterial,
    CourseMaterialChapter,
    Homework,
    HomeworkSubmission,
    Student,
    Subject,
    User,
    UserRole,
)
from fastapi.testclient import TestClient


def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
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
        tpro = db.query(User).filter(User.username == "teacher_pro").first()
        assert tpro is not None and tpro.role == UserRole.TEACHER.value
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
        assert hw.reference_answer and "教师侧" in (hw.reference_answer or "")
        assert (hw.rubric_staff_only or "").strip()
        assert hw.max_submissions == 3
        assert hw.due_date is not None
        llm = db.query(Subject).filter(Subject.name == "大语言模型").first()
        assert llm is not None
        assert llm.course_type == "elective"
        assert db.query(CourseMaterial).filter(CourseMaterial.subject_id == llm.id).count() >= 1
        assert db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == hw.id).count() >= 3
        req_cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == course.id).first()
        assert req_cfg is not None and req_cfg.is_enabled is True
        assert db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == req_cfg.id).count() >= 1
        el_cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == llm.id).first()
        assert el_cfg is not None
        assert el_cfg.is_enabled is True
        assert db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == el_cfg.id).count() >= 1
        llm_hw = (
            db.query(Homework)
            .filter(Homework.subject_id == llm.id, Homework.title.contains("大语言模型"))
            .first()
        )
        assert llm_hw is not None and llm_hw.auto_grading_enabled is True

        prob = db.query(Subject).filter(Subject.name == "初等概率论").first()
        assert prob is not None
        assert prob.course_type == "elective"
        assert prob.teacher_id == tpro.id
        assert "Bayes" in (prob.description or "")
        assert db.query(CourseMaterial).filter(CourseMaterial.subject_id == prob.id).count() >= 1
        prob_hw = (
            db.query(Homework)
            .filter(Homework.subject_id == prob.id, Homework.title.contains("初等概率论"))
            .first()
        )
        assert prob_hw is not None
        assert prob_hw.auto_grading_enabled is True
        assert (prob_hw.rubric_staff_only or "").strip()
        assert (prob_hw.reference_answer or "").strip()
        students_by_no = {
            row.student_no: row for row in db.query(Student).filter(Student.class_id == course.class_id).all()
        }
        enrolled_ids = {
            row.student_id
            for row in db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == prob.id).all()
        }
        assert students_by_no["stu1"].id in enrolled_ids
        assert students_by_no["stu2"].id in enrolled_ids
        assert students_by_no["stu4"].id in enrolled_ids
        assert students_by_no["stu3"].id not in enrolled_ids
        assert students_by_no["stu5"].id not in enrolled_ids
        assert db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == prob_hw.id).count() >= 2
        prob_cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == prob.id).first()
        assert prob_cfg is not None and prob_cfg.is_enabled is True
        assert db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == prob_cfg.id).count() >= 1
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


def test_demo_teacher_pro_can_login():
    _reset_db()
    db = SessionLocal()
    try:
        seed_demo_course_bundle(db)
    finally:
        db.close()

    client = TestClient(app)
    r = client.post("/api/auth/login", data={"username": "teacher_pro", "password": "teacher_pro"})
    assert r.status_code == 200, r.text
