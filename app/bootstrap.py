import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.attachments import ensure_upload_directories
from app.auth import get_password_hash
from app.config import settings
from app.course_access import sync_course_enrollments
from app.database import Base, SessionLocal, engine
from app.llm_grading import validate_text_connectivity, validate_vision_connectivity
from app.models import (
    Class,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    HomeworkAttempt,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMEndpointPreset,
    LLMGroup,
    LLMTokenUsageLog,
    Score,
    Semester,
    Student,
    Subject,
    SystemSetting,
    User,
    UserRole,
)


DEFAULT_SEMESTERS = [
    {"name": "2024-\u6625\u5b63", "year": 2024},
    {"name": "2024-\u79cb\u5b63", "year": 2024},
    {"name": "2025-\u6625\u5b63", "year": 2025},
    {"name": "2025-\u79cb\u5b63", "year": 2025},
    {"name": "2026-\u6625\u5b63", "year": 2026},
    {"name": "2026-\u79cb\u5b63", "year": 2026},
]

DEFAULT_SYSTEM_SETTINGS = [
    ("system_name", "BIMSA-CLASS", "System display name."),
    ("login_background", "", "Custom login background URL."),
    ("system_logo", "", "Custom system logo URL."),
    ("system_intro", "University teaching management platform", "Short introduction shown on the login page."),
    ("copyright", "(c) 2026 BIMSA-CLASS", "Footer copyright text."),
    ("use_bing_background", "true", "Whether the login page should use the daily Bing background."),
]

LEGACY_SYSTEM_SETTING_VALUES = {
    "system_name": {"DD-CLASS", "DD-CLASS 班级管理系统"},
    "copyright": {"(c) 2026 DD-CLASS", "漏 2024 DD-CLASS"},
}

DEMO_SEED_CLASS_NAME = "\u6f14\u793a\u73ed\u7ea7"
DEMO_SEED_COURSE_NAME = "\u6f14\u793a\u8bfe\u7a0b\uff08\u7cfb\u7edf\u793a\u4f8b\uff09"
DEMO_SEED_HOMEWORK_TITLE = "\u793a\u4f8b\u4f5c\u4e1a\uff08\u7b2c\u4e00\u5468\uff09"

DEFAULT_COURSE_LLM_SYSTEM_PROMPT = (
    "\u4f60\u662f\u672c\u8bfe\u7a0b\u7684\u667a\u80fd\u6559\u5b66\u52a9\u6559\uff0c\u56de\u7b54\u5b66\u751f\u95ee\u9898\u65f6\u7b80\u6d01\u3001\u51c6\u786e\uff0c"
    "\u5f15\u7528\u8bfe\u7a0b\u5927\u7eb2\u4e0e\u4f5c\u4e1a\u8981\u6c42\uff0c\u4e0d\u6cc4\u9732\u4ec5\u6559\u5e08\u53ef\u89c1\u7684\u8bc4\u5206\u7ec6\u5219\u6216\u53c2\u8003\u7b54\u6848\u3002"
)

DEFAULT_COURSE_LLM_TEACHER_PROMPT = (
    "\u81ea\u52a8\u8bc4\u5206\u65f6\uff1a\u4e25\u683c\u9075\u5faa\u300c\u5bf9\u5b66\u751f\u53ef\u89c1\u7684\u8bc4\u5206\u8981\u70b9\u300d\uff0c\u5e76\u7efc\u5408\u300c\u4ec5\u6559\u5e08\u53ef\u89c1\u7684\u8bc4\u5206\u8981\u70b9\u300d"
    "\u4e0e\u300c\u53c2\u8003\u7b54\u6848\u6216\u601d\u8def\u300d\u8fdb\u884c\u5224\u5206\uff1b\u8f93\u51fa\u5206\u6570\u4e0e\u7b80\u77ed\u8bc4\u8bed\uff0c\u4e0d\u8981\u6cc4\u9732\u672a\u516c\u5f00\u8981\u70b9\u7684\u539f\u6587\u7ed9\u5b66\u751f\u3002"
)


def normalize_legacy_branding(value: str) -> str:
    if not value:
        return value
    return re.sub(r"dd-class", "BIMSA-CLASS", value, flags=re.IGNORECASE)


def ensure_schema_updates() -> None:
    alter_statements = [
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS teacher_id INTEGER REFERENCES users(id)",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS class_id INTEGER REFERENCES classes(id)",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS semester_id INTEGER REFERENCES semesters(id)",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS course_type VARCHAR NOT NULL DEFAULT 'required'",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'active'",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS semester VARCHAR",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS weekly_schedule VARCHAR",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS course_start_at TIMESTAMP",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS course_end_at TIMESTAMP",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS course_times TEXT",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS description VARCHAR",
        "ALTER TABLE subjects ADD COLUMN IF NOT EXISTS cover_image_url VARCHAR",
        "ALTER TABLE course_enrollments ADD COLUMN IF NOT EXISTS enrollment_type VARCHAR NOT NULL DEFAULT 'required'",
        """
        CREATE TABLE IF NOT EXISTS course_exam_weights (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            exam_type VARCHAR NOT NULL,
            weight FLOAT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_course_exam_weight_subject_exam_type UNIQUE(subject_id, exam_type)
        )
        """,
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS subject_id INTEGER REFERENCES subjects(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS subject_id INTEGER REFERENCES subjects(id)",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS attachment_name VARCHAR",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS attachment_url VARCHAR",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS max_score FLOAT NOT NULL DEFAULT 100",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS grade_precision VARCHAR NOT NULL DEFAULT 'integer'",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS auto_grading_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS rubric_text TEXT",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS rubric_teacher_text TEXT",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS reference_answer TEXT",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS response_language VARCHAR",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS allow_late_submission BOOLEAN DEFAULT TRUE",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS late_submission_affects_score BOOLEAN DEFAULT FALSE",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS review_score FLOAT",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS review_comment VARCHAR",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS latest_attempt_id INTEGER",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS graded_best_attempt_id INTEGER",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS latest_task_status VARCHAR",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS latest_task_error TEXT",
        """
        CREATE TABLE IF NOT EXISTS homework_attempts (
            id INTEGER PRIMARY KEY,
            homework_id INTEGER NOT NULL REFERENCES homeworks(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject_id INTEGER REFERENCES subjects(id),
            class_id INTEGER NOT NULL REFERENCES classes(id),
            submission_summary_id INTEGER REFERENCES homework_submissions(id),
            content TEXT,
            attachment_name VARCHAR,
            attachment_url VARCHAR,
            is_late BOOLEAN DEFAULT FALSE,
            counts_toward_final_score BOOLEAN DEFAULT TRUE,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS homework_score_candidates (
            id INTEGER PRIMARY KEY,
            attempt_id INTEGER NOT NULL REFERENCES homework_attempts(id),
            homework_id INTEGER NOT NULL REFERENCES homeworks(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            source VARCHAR NOT NULL DEFAULT 'auto',
            score FLOAT NOT NULL,
            comment TEXT,
            created_by INTEGER REFERENCES users(id),
            source_metadata JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS homework_grading_tasks (
            id INTEGER PRIMARY KEY,
            attempt_id INTEGER NOT NULL REFERENCES homework_attempts(id),
            homework_id INTEGER NOT NULL REFERENCES homeworks(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject_id INTEGER REFERENCES subjects(id),
            status VARCHAR NOT NULL DEFAULT 'queued',
            queue_reason VARCHAR,
            error_code VARCHAR,
            error_message TEXT,
            task_summary TEXT,
            artifact_manifest JSON,
            input_token_estimate INTEGER,
            billed_input_tokens INTEGER,
            billed_output_tokens INTEGER,
            billed_total_tokens INTEGER,
            current_endpoint_index INTEGER,
            current_attempt INTEGER NOT NULL DEFAULT 0,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS llm_endpoint_presets (
            id INTEGER PRIMARY KEY,
            name VARCHAR NOT NULL UNIQUE,
            base_url VARCHAR NOT NULL,
            api_key TEXT NOT NULL,
            model_name VARCHAR NOT NULL,
            connect_timeout_seconds INTEGER NOT NULL DEFAULT 10,
            read_timeout_seconds INTEGER NOT NULL DEFAULT 120,
            max_retries INTEGER NOT NULL DEFAULT 2,
            initial_backoff_seconds INTEGER NOT NULL DEFAULT 2,
            is_active BOOLEAN DEFAULT TRUE,
            supports_vision BOOLEAN DEFAULT FALSE,
            validation_status VARCHAR NOT NULL DEFAULT 'pending',
            validation_message TEXT,
            validated_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS course_llm_configs (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL UNIQUE REFERENCES subjects(id),
            is_enabled BOOLEAN DEFAULT FALSE,
            response_language VARCHAR,
            daily_student_token_limit INTEGER,
            estimated_chars_per_token FLOAT NOT NULL DEFAULT 4.0,
            estimated_image_tokens INTEGER NOT NULL DEFAULT 850,
            max_input_tokens INTEGER NOT NULL DEFAULT 16000,
            max_output_tokens INTEGER NOT NULL DEFAULT 1200,
            quota_timezone VARCHAR NOT NULL DEFAULT 'UTC',
            system_prompt TEXT,
            teacher_prompt TEXT,
            created_by INTEGER REFERENCES users(id),
            updated_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS course_llm_config_endpoints (
            id INTEGER PRIMARY KEY,
            config_id INTEGER NOT NULL REFERENCES course_llm_configs(id),
            preset_id INTEGER NOT NULL REFERENCES llm_endpoint_presets(id),
            priority INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_course_llm_config_endpoint UNIQUE(config_id, preset_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS llm_token_usage_logs (
            id INTEGER PRIMARY KEY,
            task_id INTEGER NOT NULL UNIQUE REFERENCES homework_grading_tasks(id),
            subject_id INTEGER REFERENCES subjects(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            usage_date VARCHAR NOT NULL,
            timezone VARCHAR NOT NULL DEFAULT 'UTC',
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS attachment_name VARCHAR",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS attachment_url VARCHAR",
        """
        CREATE TABLE IF NOT EXISTS llm_groups (
            id INTEGER PRIMARY KEY,
            config_id INTEGER NOT NULL REFERENCES course_llm_configs(id) ON DELETE CASCADE,
            priority INTEGER NOT NULL DEFAULT 1,
            name VARCHAR(128),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "ALTER TABLE course_llm_config_endpoints ADD COLUMN IF NOT EXISTS group_id INTEGER REFERENCES llm_groups(id) ON DELETE SET NULL",
    ]

    with engine.begin() as connection:
        for statement in alter_statements:
            if engine.dialect.name != "sqlite":
                connection.execute(text(statement))
                continue

            sqlite_statement = (
                statement
                .replace(" ADD COLUMN IF NOT EXISTS ", " ADD COLUMN ")
                .replace(" INTEGER REFERENCES users(id)", " INTEGER")
                .replace(" INTEGER REFERENCES classes(id)", " INTEGER")
                .replace(" INTEGER REFERENCES semesters(id)", " INTEGER")
                .replace(" INTEGER REFERENCES subjects(id)", " INTEGER")
            )
            try:
                connection.execute(text(sqlite_statement))
            except OperationalError as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

        connection.execute(
            text(
                """
                UPDATE course_enrollments
                SET enrollment_type = CASE
                    WHEN can_remove THEN 'elective'
                    ELSE 'required'
                END
                WHERE enrollment_type IS NULL OR enrollment_type = ''
                """
            )
        )

    _drop_legacy_daily_course_token_limit_column()
    _backfill_default_llm_groups_for_existing_configs()


def _drop_legacy_daily_course_token_limit_column() -> None:
    """Remove per-course daily pool column; quotas are student-only (see CourseLLMConfig)."""
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE course_llm_configs DROP COLUMN IF EXISTS daily_course_token_limit"))
        return
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            rows = conn.execute(text("PRAGMA table_info(course_llm_configs)")).fetchall()
            colnames = {row[1] for row in rows}
            if "daily_course_token_limit" in colnames:
                conn.execute(text("ALTER TABLE course_llm_configs DROP COLUMN daily_course_token_limit"))
        return


def _backfill_default_llm_groups_for_existing_configs() -> None:
    """Orphan course_llm_config_endpoints -> single default group per config."""
    db = SessionLocal()
    try:
        for cfg in db.query(CourseLLMConfig).all():
            orphan_links = [row for row in (cfg.endpoints or []) if getattr(row, "group_id", None) is None]
            if not orphan_links:
                continue
            g = (
                db.query(LLMGroup)
                .filter(LLMGroup.config_id == cfg.id, LLMGroup.priority == 1, LLMGroup.name == "default")
                .first()
            )
            if not g:
                g = LLMGroup(config_id=cfg.id, priority=1, name="default")
                db.add(g)
                db.flush()
            for item in sorted(orphan_links, key=lambda r: (r.priority, r.id)):
                item.group_id = g.id
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def backfill_homework_grading_data(db) -> None:
    created_attempts = 0
    created_candidates = 0
    updated_configs = 0
    updated_submission_links = 0

    for homework in db.query(Homework).all():
        if homework.subject_id:
            config = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == homework.subject_id).first()
            if not config:
                db.add(CourseLLMConfig(subject_id=homework.subject_id))
                updated_configs += 1

    submissions = db.query(HomeworkSubmission).all()
    for submission in submissions:
        attempt = None
        if submission.latest_attempt_id:
            attempt = db.query(HomeworkAttempt).filter(HomeworkAttempt.id == submission.latest_attempt_id).first()

        if not attempt:
            attempt = (
                db.query(HomeworkAttempt)
                .filter(
                    HomeworkAttempt.homework_id == submission.homework_id,
                    HomeworkAttempt.student_id == submission.student_id,
                    HomeworkAttempt.submission_summary_id == submission.id,
                )
                .order_by(HomeworkAttempt.submitted_at.desc(), HomeworkAttempt.id.desc())
                .first()
            )

        if not attempt:
            homework = db.query(Homework).filter(Homework.id == submission.homework_id).first()
            is_late = False
            counts_toward = True
            if homework and homework.due_date and submission.submitted_at:
                is_late = submission.submitted_at > homework.due_date
                counts_toward = (not is_late) or (not bool(homework.late_submission_affects_score))
            attempt = HomeworkAttempt(
                homework_id=submission.homework_id,
                student_id=submission.student_id,
                subject_id=submission.subject_id,
                class_id=submission.class_id,
                submission_summary_id=submission.id,
                content=submission.content,
                attachment_name=submission.attachment_name,
                attachment_url=submission.attachment_url,
                is_late=is_late,
                counts_toward_final_score=counts_toward,
                submitted_at=submission.submitted_at,
                updated_at=submission.updated_at,
            )
            db.add(attempt)
            db.flush()
            created_attempts += 1

        if submission.latest_attempt_id != attempt.id:
            submission.latest_attempt_id = attempt.id
            updated_submission_links += 1

        if submission.review_score is not None:
            existing_candidate = (
                db.query(HomeworkScoreCandidate)
                .filter(
                    HomeworkScoreCandidate.attempt_id == attempt.id,
                    HomeworkScoreCandidate.source == "teacher",
                    HomeworkScoreCandidate.score == submission.review_score,
                )
                .first()
            )
            if not existing_candidate:
                db.add(
                    HomeworkScoreCandidate(
                        attempt_id=attempt.id,
                        homework_id=submission.homework_id,
                        student_id=submission.student_id,
                        source="teacher",
                        score=submission.review_score,
                        comment=submission.review_comment,
                        source_metadata={"legacy_migration": True},
                        created_at=submission.updated_at or submission.submitted_at,
                        updated_at=submission.updated_at or submission.submitted_at,
                    )
                )
                created_candidates += 1

    if created_attempts or created_candidates or updated_configs or updated_submission_links:
        db.commit()
    print(
        "Backfilled homework grading data. "
        "Attempts: "
        f"{created_attempts}, candidates: {created_candidates}, configs: {updated_configs}, "
        f"submission_links: {updated_submission_links}."
    )


def seed_default_admin(db) -> None:
    existing_admin = db.query(User).filter(User.username == settings.INIT_ADMIN_USERNAME).first()
    if existing_admin:
        print(f"Admin user '{settings.INIT_ADMIN_USERNAME}' already exists.")
        return

    admin_user = User(
        username=settings.INIT_ADMIN_USERNAME,
        hashed_password=get_password_hash(settings.INIT_ADMIN_PASSWORD),
        real_name=settings.INIT_ADMIN_REAL_NAME,
        role="admin",
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    print(f"Created bootstrap admin '{settings.INIT_ADMIN_USERNAME}'.")


def seed_default_semesters(db) -> None:
    created = 0
    for semester in DEFAULT_SEMESTERS:
        exists = db.query(Semester).filter(Semester.name == semester["name"]).first()
        if exists:
            continue
        db.add(Semester(name=semester["name"], year=semester["year"], is_active=True))
        created += 1

    if created:
        db.commit()
    print(f"Ensured default semesters. Added {created} item(s).")


def normalize_semester_name(name: str | None) -> str | None:
    if not name:
        return name

    normalized = name.strip()
    match = re.fullmatch(r"(\d{4})-(1|2)", normalized)
    if not match:
        return normalized

    year, term = match.groups()
    return f"{year}-\u6625\u5b63" if term == "1" else f"{year}-\u79cb\u5b63"


def normalize_semester_catalog(db) -> None:
    semesters = db.query(Semester).order_by(Semester.created_at.asc(), Semester.id.asc()).all()
    changed = 0

    for semester in semesters:
        normalized_name = normalize_semester_name(semester.name)
        if not normalized_name or normalized_name == semester.name:
            continue

        old_name = semester.name
        existing = db.query(Semester).filter(Semester.name == normalized_name).first()
        if existing and existing.id != semester.id:
            db.query(Subject).filter(Subject.semester_id == semester.id).update(
                {Subject.semester_id: existing.id},
                synchronize_session=False
            )
            db.query(Subject).filter(Subject.semester == old_name).update(
                {Subject.semester: normalized_name},
                synchronize_session=False
            )
            db.query(Score).filter(Score.semester == old_name).update(
                {Score.semester: normalized_name},
                synchronize_session=False
            )
            db.delete(semester)
            changed += 1
            continue

        semester.name = normalized_name
        if normalized_name[:4].isdigit():
            semester.year = int(normalized_name[:4])
        db.query(Subject).filter(Subject.semester == old_name).update(
            {Subject.semester: normalized_name},
            synchronize_session=False
        )
        db.query(Score).filter(Score.semester == old_name).update(
            {Score.semester: normalized_name},
            synchronize_session=False
        )
        changed += 1

    if changed:
        db.commit()
    print(f"Normalized semester catalog. Updated {changed} item(s).")


def sync_subject_semester_links(db) -> None:
    semesters = db.query(Semester).order_by(Semester.year.asc(), Semester.created_at.asc(), Semester.id.asc()).all()
    semesters_by_name = {semester.name: semester for semester in semesters}
    updated = 0

    for course in db.query(Subject).all():
        matched_semester = None

        if course.semester_id:
            matched_semester = next((semester for semester in semesters if semester.id == course.semester_id), None)

        if not matched_semester and course.semester:
            normalized_name = normalize_semester_name(course.semester)
            matched_semester = semesters_by_name.get(normalized_name)

        if not matched_semester:
            continue

        if course.semester_id != matched_semester.id:
            course.semester_id = matched_semester.id
            updated += 1

        if course.semester != matched_semester.name:
            course.semester = matched_semester.name
            updated += 1

    if updated:
        db.commit()
    print(f"Ensured subject semester links. Updated {updated} field(s).")


def seed_default_system_settings(db) -> None:
    created = 0
    updated = 0
    for key, value, description in DEFAULT_SYSTEM_SETTINGS:
        exists = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if exists:
            normalized_value = normalize_legacy_branding(exists.setting_value)
            if exists.setting_value in LEGACY_SYSTEM_SETTING_VALUES.get(key, set()) or normalized_value != exists.setting_value:
                exists.setting_value = normalized_value if normalized_value else value
                exists.description = description
                updated += 1
            continue
        db.add(
            SystemSetting(
                setting_key=key,
                setting_value=value,
                description=description,
            )
        )
        created += 1

    if created or updated:
        db.commit()
    print(f"Ensured default system settings. Added {created} item(s), updated {updated} item(s).")


def normalize_teacher_class_assignments(db) -> None:
    updated = (
        db.query(User)
        .filter(User.role == UserRole.TEACHER.value, User.class_id.isnot(None))
        .update({User.class_id: None}, synchronize_session=False)
    )
    if updated:
        db.commit()
    print(f"Ensured teacher class assignments. Cleared {updated} item(s).")


def sync_existing_courses(db) -> None:
    synced = 0
    courses = db.query(Subject).filter(Subject.class_id.isnot(None)).all()
    for course in courses:
        synced += sync_course_enrollments(course, db)

    if synced:
        db.commit()
    print(f"Ensured course enrollments. Added {synced} item(s).")


def _wire_course_llm_from_preset(db, subject_id: int, preset: LLMEndpointPreset, acting_user_id: Optional[int]) -> None:
    """Enable course LLM, attach validated vision preset, set default assistant + grading hints."""
    config = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == subject_id).first()
    if not config:
        config = CourseLLMConfig(subject_id=subject_id, created_by=acting_user_id, updated_by=acting_user_id)
        db.add(config)
        db.flush()
    config.is_enabled = True
    if not (config.response_language or "").strip():
        config.response_language = "zh-CN"
    if not (config.system_prompt or "").strip():
        config.system_prompt = DEFAULT_COURSE_LLM_SYSTEM_PROMPT
    if not (config.teacher_prompt or "").strip():
        config.teacher_prompt = DEFAULT_COURSE_LLM_TEACHER_PROMPT
    config.updated_by = acting_user_id
    db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == config.id).delete()
    db.query(LLMGroup).filter(LLMGroup.config_id == config.id).delete()
    db.flush()
    group = LLMGroup(config_id=config.id, priority=1, name="default")
    db.add(group)
    db.flush()
    db.add(
        CourseLLMConfigEndpoint(
            config_id=config.id,
            group_id=group.id,
            preset_id=preset.id,
            priority=1,
        )
    )


def _seed_demo_homework_submissions(db, homework: Homework, students: list[Student]) -> None:
    if db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework.id).count() > 0:
        return
    now = datetime.now(timezone.utc)
    samples = [
        "\u672c\u5468\u5b66\u4e60\u4e86\u8bfe\u7a0b\u5bfc\u8bba\uff0c\u4e86\u89e3\u4e86\u8003\u6838\u65b9\u5f0f\u4e0e\u4f5c\u4e1a\u63d0\u4ea4\u89c4\u5219\uff0c\u5c06\u6309\u65f6\u5b8c\u6210\u540e\u7eed\u7ec3\u4e60\u3002",
        "\u7b2c\u4e00\u5468\u5185\u5bb9\u5305\u62ec\u5b66\u4e60\u76ee\u6807\u3001\u8bfe\u7a0b\u5927\u7eb2\u4e0e\u5148\u4fee\u8981\u6c42\uff0c\u6211\u5df2\u6839\u636e\u6559\u5e08\u63d0\u793a\u6574\u7406\u7b14\u8bb0\u5e76\u9884\u4e60\u4e0b\u4e00\u8282\u3002",
    ]
    for idx, st in enumerate(students[:2]):
        content = samples[idx % len(samples)]
        sub = HomeworkSubmission(
            homework_id=homework.id,
            student_id=st.id,
            subject_id=homework.subject_id,
            class_id=homework.class_id,
            content=content,
            submitted_at=now - timedelta(hours=3 - idx),
            updated_at=now - timedelta(hours=3 - idx),
        )
        db.add(sub)
        db.flush()
        attempt = HomeworkAttempt(
            homework_id=homework.id,
            student_id=st.id,
            subject_id=homework.subject_id,
            class_id=homework.class_id,
            submission_summary_id=sub.id,
            content=content,
            is_late=False,
            counts_toward_final_score=True,
            submitted_at=sub.submitted_at,
            updated_at=sub.updated_at,
        )
        db.add(attempt)
        db.flush()
        sub.latest_attempt_id = attempt.id


def seed_initial_llm_deployment_bundle(db) -> None:
    """When INIT_LLM_* env is set, upsert a preset, run text+vision probe (image), wire demo course LLM + homework."""
    api_key = (settings.INIT_LLM_API_KEY or "").strip()
    base_url = (settings.INIT_LLM_BASE_URL or "").strip()
    model_name = (settings.INIT_LLM_MODEL_NAME or "").strip()
    if not (api_key and base_url and model_name):
        return

    preset_name = (settings.INIT_LLM_PRESET_NAME or "deployment-primary").strip() or "deployment-primary"
    ct = int(settings.INIT_LLM_CONNECT_TIMEOUT_SECONDS or 10)
    rt = int(settings.INIT_LLM_READ_TIMEOUT_SECONDS or 120)

    preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.name == preset_name).first()
    if preset:
        preset.base_url = base_url
        preset.api_key = api_key
        preset.model_name = model_name
        preset.connect_timeout_seconds = ct
        preset.read_timeout_seconds = rt
        preset.is_active = True
    else:
        preset = LLMEndpointPreset(
            name=preset_name,
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            connect_timeout_seconds=ct,
            read_timeout_seconds=rt,
            is_active=True,
        )
        db.add(preset)
    db.flush()

    ok_t, msg_t = validate_text_connectivity(
        base_url=preset.base_url,
        api_key=preset.api_key,
        model_name=preset.model_name,
        connect_timeout_seconds=preset.connect_timeout_seconds,
        read_timeout_seconds=preset.read_timeout_seconds,
    )
    if not ok_t:
        preset.validation_status = "failed"
        preset.validation_message = msg_t
        preset.supports_vision = False
    else:
        ok_v, msg_v = validate_vision_connectivity(
            base_url=preset.base_url,
            api_key=preset.api_key,
            model_name=preset.model_name,
            connect_timeout_seconds=preset.connect_timeout_seconds,
            read_timeout_seconds=preset.read_timeout_seconds,
        )
        ok = ok_v
        message = f"{msg_t} {msg_v}" if ok_v else msg_v
        preset.validation_status = "validated" if ok else "failed"
        preset.validation_message = message
        preset.supports_vision = bool(ok_v)
    preset.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preset)

    if preset.validation_status != "validated" or not preset.supports_vision:
        print(
            f"INIT_LLM: endpoint '{preset_name}' did not pass vision validation; "
            f"demo course wiring skipped. Message: {preset.validation_message}"
        )
        return

    admin = db.query(User).filter(User.username == settings.INIT_ADMIN_USERNAME).first()
    if not admin:
        print("INIT_LLM: bootstrap admin user not found; skipping demo course seed.")
        return
    acting_id = admin.id

    demo_course = db.query(Subject).filter(Subject.name == DEMO_SEED_COURSE_NAME).first()
    if not demo_course:
        semester = (
            db.query(Semester)
            .filter(Semester.is_active.is_(True))
            .order_by(Semester.year.desc(), Semester.id.desc())
            .first()
        )
        if not semester:
            semester = db.query(Semester).order_by(Semester.id.asc()).first()
        if not semester:
            print("INIT_LLM: no semester row found; cannot seed demo course.")
            return

        demo_class = db.query(Class).filter(Class.name == DEMO_SEED_CLASS_NAME).first()
        if not demo_class:
            demo_class = Class(name=DEMO_SEED_CLASS_NAME, grade=1)
            db.add(demo_class)
            db.flush()

        demo_students_spec = [
            ("\u5f20\u4e09", "demo-2026-001"),
            ("\u674e\u56db", "demo-2026-002"),
            ("\u738b\u4e94", "demo-2026-003"),
            ("\u8d75\u516d", "demo-2026-004"),
        ]
        students: list[Student] = []
        for st_name, st_no in demo_students_spec:
            existing = (
                db.query(Student)
                .filter(Student.class_id == demo_class.id, Student.student_no == st_no)
                .first()
            )
            if existing:
                students.append(existing)
                continue
            st = Student(name=st_name, student_no=st_no, class_id=demo_class.id, teacher_id=acting_id)
            db.add(st)
            db.flush()
            students.append(st)

        demo_course = Subject(
            name=DEMO_SEED_COURSE_NAME,
            teacher_id=acting_id,
            class_id=demo_class.id,
            semester_id=semester.id,
            course_type="required",
            status="active",
            semester=semester.name,
            description="\u7cfb\u7edf\u521d\u59cb\u5316\u6f14\u793a\u8bfe\u7a0b\uff08\u53ef\u5220\u9664\u6216\u6539\u7f16\uff09\u3002",
        )
        db.add(demo_course)
        db.flush()
        sync_course_enrollments(demo_course, db)

        hw = Homework(
            title=DEMO_SEED_HOMEWORK_TITLE,
            content="\u8bf7\u6839\u636e\u7b2c\u4e00\u5468\u8bfe\u5802\u5185\u5bb9\uff0c\u7528\u81ea\u5df1\u7684\u8bdd\u7b80\u8981\u8bf4\u660e\u672c\u5468\u5b66\u4e60\u6536\u83b7\uff08\u7eaf\u6587\u672c\u63d0\u4ea4\u5373\u53ef\uff09\u3002",
            class_id=demo_class.id,
            subject_id=demo_course.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=14),
            max_score=100,
            grade_precision="integer",
            auto_grading_enabled=True,
            rubric_text=(
                "\uff08\u5bf9\u5b66\u751f\u53ef\u89c1\uff09\u8bc4\u5206\u8981\u70b9\uff1a\u662f\u5426\u6db5\u76d6\u672c\u5468\u5b66\u4e60\u76ee\u6807\u4e0e\u81ea\u6211\u68c0\u89c6\uff1b"
                "\u8868\u8ff0\u6e05\u6670\u3001\u903b\u8f91\u5b8c\u6574\u5373\u53ef\u3002"
            ),
            rubric_teacher_text=(
                "\uff08\u4ec5\u6559\u5e08\u53ef\u89c1\uff09\u5185\u90e8\u8bc4\u5206\u7ec6\u5219\uff1a\u5173\u6ce8\u662f\u5426\u63d0\u5230\u8bfe\u7a0b\u5bfc\u8bba\u4e2d\u7684\u5173\u952e\u6982\u5ff5\uff1b\u4e0d\u8981\u56e0\u7528\u8bcd\u7ec6\u5fae\u5dee\u5f02\u8fc7\u5ea6\u6263\u5206\u3002"
            ),
            reference_answer=(
                "\uff08\u4ec5\u6559\u5e08\u53ef\u89c1\uff09\u53c2\u8003\u7b54\u6848\u6216\u601d\u8def\uff1a\u53ef\u4ece\u5b66\u4e60\u76ee\u6807\u3001\u8003\u6838\u65b9\u5f0f\u3001\u5148\u4fee/\u51c6\u5907\u5efa\u8bae\u4e09\u65b9\u9762\u62df\u5199\uff1b\u65e0\u552f\u4e00\u6807\u51c6\u7b54\u6848\u3002"
            ),
            response_language="zh-CN",
            allow_late_submission=True,
            late_submission_affects_score=False,
            created_by=acting_id,
        )
        db.add(hw)
        db.flush()
        _seed_demo_homework_submissions(db, hw, students)
    else:
        sync_course_enrollments(demo_course, db)

    _wire_course_llm_from_preset(db, demo_course.id, preset, acting_id)
    db.commit()
    print(
        f"INIT_LLM: preset '{preset_name}' validated (incl. vision image probe); "
        f"demo course '{DEMO_SEED_COURSE_NAME}' LLM enabled and linked."
    )


def bootstrap() -> None:
    ensure_upload_directories()
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        normalize_teacher_class_assignments(db)
        normalize_semester_catalog(db)
        sync_subject_semester_links(db)
        backfill_homework_grading_data(db)
        if settings.INIT_DEFAULT_DATA:
            seed_default_admin(db)
            seed_default_semesters(db)
            normalize_semester_catalog(db)
            sync_subject_semester_links(db)
            seed_default_system_settings(db)
            sync_existing_courses(db)
            seed_initial_llm_deployment_bundle(db)
            from app.seed_default_probability import seed_elementary_probability_elective_course

            seed_elementary_probability_elective_course(db)
            backfill_homework_grading_data(db)
        else:
            print("INIT_DEFAULT_DATA is false. Table creation completed without seed data.")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap()
