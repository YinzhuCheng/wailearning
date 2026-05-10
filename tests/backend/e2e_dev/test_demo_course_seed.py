"""Demo course seed data (teacher + students + homework)."""

from __future__ import annotations

import json

from sqlalchemy import text

from apps.backend.courseeval_backend.db.database import Base, SessionLocal, engine
from apps.backend.courseeval_backend.domains.seed.demo import seed_demo_course_bundle
from apps.backend.courseeval_backend.core.auth import get_password_hash
from apps.backend.courseeval_backend.main import app
from apps.backend.courseeval_backend.db.models import (
    Class,
    CourseDiscussionEntry,
    CourseEnrollment,
    CourseExamWeight,
    CourseGradeScheme,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    CourseMaterial,
    CourseMaterialChapter,
    Homework,
    HomeworkAttempt,
    HomeworkSubmission,
    LearningNote,
    LearningNoteDiscussionEntry,
    Student,
    Subject,
    User,
    UserRole,
)
from fastapi.testclient import TestClient


def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.courseeval_backend.bootstrap import ensure_schema_updates

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
        required_times = json.loads(course.course_times or "[]")
        assert len(required_times) == 1
        assert required_times[0]["weekly_schedule"] == "2@7,8"
        assert course.course_start_at is not None and course.course_end_at is not None

        assert db.query(CourseGradeScheme).filter(CourseGradeScheme.subject_id == course.id).first() is not None
        exam_w = db.query(CourseExamWeight).filter(CourseExamWeight.subject_id == course.id).first()
        assert exam_w is not None
        assert exam_w.exam_type == "期末考试"

        st1 = db.query(Student).filter(Student.student_no == "stu1").first()
        assert st1 and st1.phone
        students_by_no = {
            row.student_no: row for row in db.query(Student).filter(Student.class_id == course.class_id).all()
        }

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
        st1 = students_by_no["stu1"]
        st1_attempts = (
            db.query(HomeworkAttempt)
            .filter(HomeworkAttempt.homework_id == hw.id, HomeworkAttempt.student_id == st1.id)
            .order_by(HomeworkAttempt.submitted_at.asc(), HomeworkAttempt.id.asc())
            .all()
        )
        assert len(st1_attempts) >= 2
        assert st1_attempts[-1].prior_attempt_id == st1_attempts[-2].id
        assert st1_attempts[-1].submission_mode == "revision"
        assert db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == hw.id).count() >= 3
        llm = db.query(Subject).filter(Subject.name == "大语言模型").first()
        assert llm is not None
        assert llm.course_type == "elective"
        llm_times = json.loads(llm.course_times or "[]")
        assert len(llm_times) == 1
        assert llm_times[0]["weekly_schedule"] == "4@8,9"
        assert db.query(CourseMaterial).filter(CourseMaterial.subject_id == llm.id).count() >= 1
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
        llm_submissions = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == llm_hw.id).count()
        assert llm_submissions >= 2
        llm_enrolled_ids = {
            row.student_id
            for row in db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == llm.id).all()
        }
        assert students_by_no["stu1"].id in llm_enrolled_ids
        assert students_by_no["stu3"].id in llm_enrolled_ids
        assert students_by_no["stu5"].id in llm_enrolled_ids

        prob = db.query(Subject).filter(Subject.name == "初等概率论").first()
        assert prob is not None
        assert prob.course_type == "elective"
        assert prob.teacher_id == tpro.id
        assert "Bayes" in (prob.description or "")
        prob_times = json.loads(prob.course_times or "[]")
        assert len(prob_times) == 1
        assert prob_times[0]["weekly_schedule"] == "3@3,4"
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

        sys_user = db.query(User).filter(User.username == "__system_llm_assistant__").first()
        assert sys_user is not None
        for course_row, homework_row in ((course, hw), (llm, llm_hw), (prob, prob_hw)):
            discussion_rows = (
                db.query(CourseDiscussionEntry)
                .filter(
                    CourseDiscussionEntry.subject_id == course_row.id,
                    CourseDiscussionEntry.target_type == "homework",
                    CourseDiscussionEntry.target_id == homework_row.id,
                )
                .all()
            )
            assert len(discussion_rows) >= 3
            assert any(row.message_kind == "llm_assistant" for row in discussion_rows)
            assert any(row.llm_invocation for row in discussion_rows)

        notes = db.query(LearningNote).all()
        assert len(notes) >= 3
        assert {note.subject_id for note in notes}.issuperset({course.id, llm.id, prob.id})
        assert db.query(LearningNoteDiscussionEntry).filter(
            LearningNoteDiscussionEntry.message_kind == "llm_assistant"
        ).count() >= 2
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
