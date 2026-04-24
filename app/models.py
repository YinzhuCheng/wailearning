from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    JSON,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base

import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLASS_TEACHER = "class_teacher"
    TEACHER = "teacher"
    STUDENT = "student"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    LEAVE = "leave"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    real_name = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.TEACHER.value)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class_obj = relationship("Class", back_populates="teachers")
    students = relationship("Student", back_populates="teacher")
    courses = relationship("Subject", back_populates="teacher")


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    grade = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    teachers = relationship("User", back_populates="class_obj")
    students = relationship("Student", back_populates="class_obj")
    scores = relationship("Score", back_populates="class_obj")
    attendances = relationship("Attendance", back_populates="class_obj")
    courses = relationship("Subject", back_populates="class_obj")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    student_no = Column(String, index=True)
    gender = Column(SQLEnum(Gender))
    phone = Column(String, nullable=True)
    parent_phone = Column(String, nullable=True)
    address = Column(String, nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    parent_code = Column(String, unique=True, nullable=True, index=True)
    parent_code_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("class_id", "student_no", name="uq_student_class_no"),
    )

    class_obj = relationship("Class", back_populates="students")
    teacher = relationship("User", back_populates="students")
    scores = relationship("Score", back_populates="student")
    attendances = relationship("Attendance", back_populates="student")
    course_enrollments = relationship("CourseEnrollment", back_populates="student")
    homework_submissions = relationship("HomeworkSubmission", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    semester_id = Column(Integer, ForeignKey("semesters.id"), nullable=True)
    course_type = Column(String, nullable=False, default="required")
    status = Column(String, nullable=False, default="active")
    semester = Column(String, nullable=True)
    weekly_schedule = Column(String, nullable=True)
    course_start_at = Column(DateTime(timezone=True), nullable=True)
    course_end_at = Column(DateTime(timezone=True), nullable=True)
    course_times = Column(Text, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    teacher = relationship("User", back_populates="courses")
    class_obj = relationship("Class", back_populates="courses")
    semester_obj = relationship("Semester")
    scores = relationship("Score", back_populates="subject")
    homeworks = relationship("Homework", back_populates="subject")
    attendances = relationship("Attendance", back_populates="subject")
    notifications = relationship("Notification", back_populates="subject")
    materials = relationship("CourseMaterial", back_populates="subject")
    enrollments = relationship("CourseEnrollment", back_populates="course")
    llm_config = relationship("CourseLLMConfig", back_populates="subject", uselist=False)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    enrollment_type = Column(String, nullable=False, default="required")
    can_remove = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("subject_id", "student_id", name="uq_course_enrollment"),
    )

    course = relationship("Subject", back_populates="enrollments")
    student = relationship("Student", back_populates="course_enrollments")
    class_obj = relationship("Class")


class CourseEnrollmentBlock(Base):
    """
    Records that a student was explicitly removed from a course enrollment.
    Student-side auto sync (prepare_student_course_context) must not recreate
    that row; teacher roster sync (sync_course_enrollments) clears the block
    when re-adding the student from the class roster.
    """

    __tablename__ = "course_enrollment_blocks"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("subject_id", "student_id", name="uq_course_enrollment_block"),)

    course = relationship("Subject")
    student = relationship("Student")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    score = Column(Float, nullable=False)
    exam_type = Column(String, default="midterm")
    exam_date = Column(DateTime(timezone=True), nullable=True)
    semester = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="scores")
    subject = relationship("Subject", back_populates="scores")
    class_obj = relationship("Class", back_populates="scores")


class CourseExamWeight(Base):
    __tablename__ = "course_exam_weights"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    exam_type = Column(String, nullable=False)
    weight = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("subject_id", "exam_type", name="uq_course_exam_weight_subject_exam_type"),
    )

    subject = relationship("Subject")


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    status = Column(SQLEnum(AttendanceStatus), default=AttendanceStatus.PRESENT)
    remark = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="attendances")
    class_obj = relationship("Class", back_populates="attendances")
    subject = relationship("Subject", back_populates="attendances")


class Semester(Base):
    __tablename__ = "semesters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    year = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=True)
    target_name = Column(String, nullable=True)
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    result = Column(String, default="success")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PointRule(Base):
    __tablename__ = "point_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False)
    points = Column(Integer, nullable=False)
    condition_type = Column(String, nullable=False)
    condition_value = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class StudentPoint(Base):
    __tablename__ = "student_points"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, unique=True)
    total_points = Column(Integer, default=0)
    available_points = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("Student", backref="point_account")


class PointRecord(Base):
    __tablename__ = "point_records"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    rule_id = Column(Integer, ForeignKey("point_rules.id"), nullable=True)
    points = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    source_type = Column(String, nullable=False)
    source_id = Column(Integer, nullable=True)
    description = Column(String, nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", backref="point_records")
    rule = relationship("PointRule", backref="records")
    operator = relationship("User", backref="point_operations")


class PointItem(Base):
    __tablename__ = "point_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    item_type = Column(String, nullable=False)
    points_cost = Column(Integer, nullable=False)
    stock = Column(Integer, default=-1)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PointExchange(Base):
    __tablename__ = "point_exchanges"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("point_items.id"), nullable=False)
    points_spent = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)
    status = Column(String, default="pending")
    exchange_time = Column(DateTime(timezone=True), server_default=func.now())
    pickup_time = Column(DateTime(timezone=True), nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    remark = Column(String, nullable=True)

    student = relationship("Student", backref="exchanges")
    item = relationship("PointItem", backref="exchanges")
    operator = relationship("User", backref="exchange_operations")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, nullable=False, index=True)
    setting_value = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_url = Column(String, nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    max_score = Column(Float, nullable=False, default=100)
    grade_precision = Column(String, nullable=False, default="integer")
    auto_grading_enabled = Column(Boolean, default=False)
    rubric_text = Column(Text, nullable=True)
    reference_answer = Column(Text, nullable=True)
    response_language = Column(String, nullable=True)
    allow_late_submission = Column(Boolean, default=True)
    late_submission_affects_score = Column(Boolean, default=False)
    max_submissions = Column(Integer, nullable=True)
    llm_routing_spec = Column(JSON, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    class_obj = relationship("Class", backref="homeworks")
    subject = relationship("Subject", back_populates="homeworks")
    creator = relationship("User", backref="homeworks")
    submissions = relationship("HomeworkSubmission", back_populates="homework")
    attempts = relationship("HomeworkAttempt", back_populates="homework")


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    content = Column(String, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_url = Column(String, nullable=True)
    review_score = Column(Float, nullable=True)
    review_comment = Column(String, nullable=True)
    latest_attempt_id = Column(Integer, ForeignKey("homework_attempts.id", use_alter=True), nullable=True)
    latest_task_status = Column(String, nullable=True)
    latest_task_error = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("homework_id", "student_id", name="uq_homework_submission_student"),
    )

    homework = relationship("Homework", back_populates="submissions")
    student = relationship("Student", back_populates="homework_submissions")
    subject = relationship("Subject")
    class_obj = relationship("Class")
    latest_attempt = relationship("HomeworkAttempt", foreign_keys=[latest_attempt_id])


class HomeworkAttempt(Base):
    __tablename__ = "homework_attempts"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    submission_summary_id = Column(Integer, ForeignKey("homework_submissions.id", use_alter=True), nullable=True)
    content = Column(Text, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_url = Column(String, nullable=True)
    is_late = Column(Boolean, default=False)
    counts_toward_final_score = Column(Boolean, default=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    homework = relationship("Homework", back_populates="attempts")
    student = relationship("Student")
    subject = relationship("Subject")
    class_obj = relationship("Class")
    summary = relationship("HomeworkSubmission", foreign_keys=[submission_summary_id], backref="attempts")
    score_candidates = relationship("HomeworkScoreCandidate", back_populates="attempt")
    grading_tasks = relationship("HomeworkGradingTask", back_populates="attempt")


class HomeworkScoreCandidate(Base):
    __tablename__ = "homework_score_candidates"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("homework_attempts.id"), nullable=False)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    source = Column(String, nullable=False, default="auto")
    score = Column(Float, nullable=False)
    comment = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    source_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    attempt = relationship("HomeworkAttempt", back_populates="score_candidates")
    homework = relationship("Homework")
    student = relationship("Student")
    creator = relationship("User")


class HomeworkGradingTask(Base):
    __tablename__ = "homework_grading_tasks"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("homework_attempts.id"), nullable=False)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    status = Column(String, nullable=False, default="queued")
    queue_reason = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    task_summary = Column(Text, nullable=True)
    artifact_manifest = Column(JSON, nullable=True)
    input_token_estimate = Column(Integer, nullable=True)
    billed_input_tokens = Column(Integer, nullable=True)
    billed_output_tokens = Column(Integer, nullable=True)
    billed_total_tokens = Column(Integer, nullable=True)
    current_endpoint_index = Column(Integer, nullable=True)
    current_attempt = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    attempt = relationship("HomeworkAttempt", back_populates="grading_tasks")
    homework = relationship("Homework")
    student = relationship("Student")
    subject = relationship("Subject")


class LLMEndpointPreset(Base):
    __tablename__ = "llm_endpoint_presets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    base_url = Column(String, nullable=False)
    api_key = Column(Text, nullable=False)
    model_name = Column(String, nullable=False)
    connect_timeout_seconds = Column(Integer, nullable=False, default=10)
    read_timeout_seconds = Column(Integer, nullable=False, default=120)
    max_retries = Column(Integer, nullable=False, default=2)
    initial_backoff_seconds = Column(Integer, nullable=False, default=2)
    is_active = Column(Boolean, default=True)
    supports_vision = Column(Boolean, default=False)
    validation_status = Column(String, nullable=False, default="pending")
    validation_message = Column(Text, nullable=True)
    text_validation_status = Column(String, nullable=True)
    text_validation_message = Column(Text, nullable=True)
    vision_validation_status = Column(String, nullable=True)
    vision_validation_message = Column(Text, nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    course_links = relationship("CourseLLMConfigEndpoint", back_populates="preset")


class CourseLLMConfig(Base):
    __tablename__ = "course_llm_configs"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, unique=True)
    is_enabled = Column(Boolean, default=False)
    response_language = Column(String, nullable=True)
    estimated_chars_per_token = Column(Float, nullable=False, default=4.0)
    estimated_image_tokens = Column(Integer, nullable=False, default=850)
    max_input_tokens = Column(Integer, nullable=False, default=16000)
    max_output_tokens = Column(Integer, nullable=False, default=1200)
    system_prompt = Column(Text, nullable=True)
    teacher_prompt = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    subject = relationship("Subject", back_populates="llm_config")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    groups = relationship(
        "LLMGroup",
        back_populates="config",
        order_by="LLMGroup.priority.asc()",
        cascade="all, delete-orphan",
    )
    endpoints = relationship(
        "CourseLLMConfigEndpoint",
        back_populates="config",
        order_by="CourseLLMConfigEndpoint.priority.asc()",
        cascade="all, delete-orphan",
    )


class LLMGroup(Base):
    __tablename__ = "llm_groups"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("course_llm_configs.id", ondelete="CASCADE"), nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    name = Column(String(128), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    config = relationship("CourseLLMConfig", back_populates="groups")
    members = relationship(
        "CourseLLMConfigEndpoint",
        back_populates="group",
        order_by="CourseLLMConfigEndpoint.priority.asc()",
        cascade="all, delete-orphan",
    )


class CourseLLMConfigEndpoint(Base):
    __tablename__ = "course_llm_config_endpoints"

    id = Column(Integer, primary_key=True, index=True)
    config_id = Column(Integer, ForeignKey("course_llm_configs.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Integer, ForeignKey("llm_groups.id", ondelete="CASCADE"), nullable=True)
    preset_id = Column(Integer, ForeignKey("llm_endpoint_presets.id"), nullable=False)
    priority = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("config_id", "preset_id", name="uq_course_llm_config_endpoint"),
    )

    config = relationship("CourseLLMConfig", back_populates="endpoints")
    group = relationship("LLMGroup", back_populates="members")
    preset = relationship("LLMEndpointPreset", back_populates="course_links")


class LLMTokenUsageLog(Base):
    __tablename__ = "llm_token_usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("homework_grading_tasks.id"), nullable=False, unique=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    usage_date = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    billing_note = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("HomeworkGradingTask")
    subject = relationship("Subject")
    student = relationship("Student")


class LLMQuotaReservation(Base):
    """
    In-flight reservation of estimated tokens against daily caps (PostgreSQL advisory lock + row).
    Released after billing or on task failure so concurrent workers share one global budget.
    """

    __tablename__ = "llm_quota_reservations"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("homework_grading_tasks.id"), nullable=False, unique=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    usage_date = Column(String, nullable=False)
    timezone = Column(String, nullable=False, default="UTC")
    reserved_tokens = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("HomeworkGradingTask")


class LLMGlobalQuotaPolicy(Base):
    """
    Singleton-style row (id=1): system-wide calendar for LLM usage logs and default per-student daily cap.
    Administrators may raise/lower defaults or change quota_timezone; teachers do not edit these fields.
    """

    __tablename__ = "llm_global_quota_policies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    default_daily_student_tokens = Column(Integer, nullable=False, default=100_000)
    quota_timezone = Column(String, nullable=False, default="Asia/Shanghai")
    max_parallel_grading_tasks = Column(Integer, nullable=False, default=3)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LLMStudentTokenOverride(Base):
    """Optional per-student daily LLM token cap (all courses share one usage pool under policy calendar)."""

    __tablename__ = "llm_student_token_overrides"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, unique=True)
    daily_tokens = Column(Integer, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("Student", backref="llm_token_override")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_url = Column(String, nullable=True)
    priority = Column(String, default="normal")
    is_pinned = Column(Boolean, default=False)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User", backref="notifications")
    class_obj = relationship("Class", backref="notifications")
    subject = relationship("Subject", back_populates="notifications")


class CourseMaterial(Base):
    __tablename__ = "course_materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=True)
    attachment_name = Column(String, nullable=True)
    attachment_url = Column(String, nullable=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    class_obj = relationship("Class", backref="materials")
    subject = relationship("Subject", back_populates="materials")
    creator = relationship("User", backref="materials")


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    notification = relationship("Notification", backref="read_records")
    user = relationship("User", backref="notification_reads")
