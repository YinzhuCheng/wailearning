import os
import re
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from apps.backend.wailearning_backend.attachments import ensure_upload_directories
from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.core.config import settings
from apps.backend.wailearning_backend.domains.courses.access import sync_course_enrollments
from apps.backend.wailearning_backend.domains.seed.demo import seed_demo_course_bundle
from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.semester_utils import DEFAULT_SEMESTERS, normalize_semester_name
from apps.backend.wailearning_backend.domains.roster.sync import reconcile_student_users_and_roster
from apps.backend.wailearning_backend.db.models import (
    CourseMaterial,
    CourseMaterialChapter,
    CourseMaterialSection,
    CourseLLMConfig,
    LLMGlobalQuotaPolicy,
    LLMGroup,
    Homework,
    HomeworkAttempt,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMEndpointPreset,
    Score,
    Semester,
    Subject,
    SystemSetting,
    User,
    UserAppearanceStyle,
    UserRole,
)


DEFAULT_SYSTEM_SETTINGS = [
    ("system_name", "BIMSA-CLASS", "System display name."),
    ("login_background", "", "Custom login background URL."),
    ("system_logo", "", "Custom system logo URL."),
    ("system_intro", "University teaching management platform", "Short introduction shown on the login page."),
    ("copyright", "(c) 2026 BIMSA-CLASS", "Footer copyright text."),
    ("use_bing_background", "true", "Whether the login page should use the daily Bing background."),
    ("appearance_default_preset", "professional-blue", "Default admin appearance preset for users who follow system style."),
]

DEFAULT_LLM_PRESET_NAME = "gpt-5.4"

LEGACY_SYSTEM_SETTING_VALUES = {
    "system_name": {"DD-CLASS", "DD-CLASS 班级管理系统"},
    "copyright": {"(c) 2026 DD-CLASS", "漏 2024 DD-CLASS"},
}


def normalize_legacy_branding(value: str) -> str:
    if not value:
        return value
    return re.sub(r"dd-class", "BIMSA-CLASS", value, flags=re.IGNORECASE)


def ensure_schema_updates() -> None:
    alter_statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0",
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
        CREATE TABLE IF NOT EXISTS course_enrollment_blocks (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_course_enrollment_block UNIQUE(subject_id, student_id)
        )
        """,
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
        """
        CREATE TABLE IF NOT EXISTS user_appearance_styles (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name VARCHAR(80) NOT NULL,
            source VARCHAR(24) NOT NULL DEFAULT 'custom',
            preset_key VARCHAR(80),
            config JSON NOT NULL DEFAULT '{}',
            is_selected BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_user_appearance_style_name UNIQUE(user_id, name)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_user_appearance_styles_user_id ON user_appearance_styles(user_id)",
        "CREATE INDEX IF NOT EXISTS ix_user_appearance_styles_is_selected ON user_appearance_styles(is_selected)",
        """
        CREATE TABLE IF NOT EXISTS homework_grade_appeals (
            id INTEGER PRIMARY KEY,
            homework_id INTEGER NOT NULL REFERENCES homeworks(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            submission_id INTEGER NOT NULL REFERENCES homework_submissions(id),
            reason_text TEXT NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS course_grade_schemes (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL UNIQUE REFERENCES subjects(id),
            homework_weight FLOAT NOT NULL DEFAULT 30,
            extra_daily_weight FLOAT NOT NULL DEFAULT 20,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS score_grade_appeals (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            score_id INTEGER REFERENCES scores(id),
            semester VARCHAR NOT NULL,
            target_component VARCHAR NOT NULL,
            reason_text TEXT NOT NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            teacher_response TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_score_grade_appeal_pending_component
        ON score_grade_appeals(subject_id, student_id, semester, target_component)
        WHERE status = 'pending'
        """,
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_read_notification_user
        ON notification_reads(notification_id, user_id)
        """,
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS target_student_id INTEGER REFERENCES students(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS related_homework_id INTEGER REFERENCES homeworks(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS related_student_id INTEGER REFERENCES students(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS related_appeal_id INTEGER REFERENCES homework_grade_appeals(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS related_score_appeal_id INTEGER REFERENCES score_grade_appeals(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS target_user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS notification_kind VARCHAR NOT NULL DEFAULT 'general'",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS attachment_name VARCHAR",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS attachment_url VARCHAR",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS max_score FLOAT NOT NULL DEFAULT 100",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS grade_precision VARCHAR NOT NULL DEFAULT 'integer'",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS auto_grading_enabled BOOLEAN DEFAULT FALSE",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS rubric_text TEXT",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS reference_answer TEXT",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS response_language VARCHAR",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS allow_late_submission BOOLEAN DEFAULT TRUE",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS late_submission_affects_score BOOLEAN DEFAULT FALSE",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS max_submissions INTEGER",
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS llm_routing_spec JSON",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS review_score FLOAT",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS review_comment VARCHAR",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS latest_attempt_id INTEGER",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS latest_task_status VARCHAR",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS latest_task_error TEXT",
        "ALTER TABLE homework_submissions ADD COLUMN IF NOT EXISTS used_llm_assist BOOLEAN NOT NULL DEFAULT FALSE",
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
            max_input_tokens INTEGER NOT NULL DEFAULT 16000,
            max_output_tokens INTEGER NOT NULL DEFAULT 1000,
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
            billing_note VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS llm_quota_reservations (
            id INTEGER PRIMARY KEY,
            task_id INTEGER NOT NULL UNIQUE REFERENCES homework_grading_tasks(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject_id INTEGER REFERENCES subjects(id),
            usage_date VARCHAR NOT NULL,
            timezone VARCHAR NOT NULL DEFAULT 'UTC',
            reserved_tokens INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS llm_global_quota_policies (
            id INTEGER PRIMARY KEY,
            default_daily_student_tokens INTEGER NOT NULL DEFAULT 100000,
            quota_timezone VARCHAR NOT NULL DEFAULT 'UTC',
            estimated_chars_per_token FLOAT NOT NULL DEFAULT 4.0,
            estimated_image_tokens INTEGER NOT NULL DEFAULT 850,
            max_parallel_grading_tasks INTEGER NOT NULL DEFAULT 3,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "ALTER TABLE llm_global_quota_policies ADD COLUMN IF NOT EXISTS estimated_chars_per_token FLOAT NOT NULL DEFAULT 4.0",
        "ALTER TABLE llm_global_quota_policies ADD COLUMN IF NOT EXISTS estimated_image_tokens INTEGER NOT NULL DEFAULT 850",
        "ALTER TABLE llm_global_quota_policies ADD COLUMN IF NOT EXISTS max_parallel_grading_tasks INTEGER NOT NULL DEFAULT 3",
        "UPDATE llm_global_quota_policies SET estimated_chars_per_token = 4.0 WHERE estimated_chars_per_token IS NULL",
        "UPDATE llm_global_quota_policies SET estimated_image_tokens = 850 WHERE estimated_image_tokens IS NULL",
        "UPDATE llm_global_quota_policies SET max_parallel_grading_tasks = 3 WHERE max_parallel_grading_tasks IS NULL",
        """
        CREATE TABLE IF NOT EXISTS llm_student_token_overrides (
            id INTEGER PRIMARY KEY,
            student_id INTEGER NOT NULL UNIQUE REFERENCES students(id),
            daily_tokens INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "ALTER TABLE llm_token_usage_logs ADD COLUMN IF NOT EXISTS billing_note VARCHAR",
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
        "ALTER TABLE llm_endpoint_presets ADD COLUMN IF NOT EXISTS text_validation_status VARCHAR",
        "ALTER TABLE llm_endpoint_presets ADD COLUMN IF NOT EXISTS text_validation_message TEXT",
        "ALTER TABLE llm_endpoint_presets ADD COLUMN IF NOT EXISTS vision_validation_status VARCHAR",
        "ALTER TABLE llm_endpoint_presets ADD COLUMN IF NOT EXISTS vision_validation_message TEXT",
        "ALTER TABLE homework_attempts ADD COLUMN IF NOT EXISTS used_llm_assist BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE homework_attempts ADD COLUMN IF NOT EXISTS submission_mode VARCHAR NOT NULL DEFAULT 'full'",
        "ALTER TABLE homework_attempts ADD COLUMN IF NOT EXISTS prior_attempt_id INTEGER",
        """
        CREATE TABLE IF NOT EXISTS course_material_chapters (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            parent_id INTEGER REFERENCES course_material_chapters(id),
            title VARCHAR NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_uncategorized BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS course_material_sections (
            id INTEGER PRIMARY KEY,
            material_id INTEGER NOT NULL REFERENCES course_materials(id) ON DELETE CASCADE,
            chapter_id INTEGER NOT NULL REFERENCES course_material_chapters(id) ON DELETE CASCADE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            CONSTRAINT uq_course_material_section_placement UNIQUE(material_id, chapter_id)
        )
        """,
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS discussion_page_size INTEGER",
        """
        CREATE TABLE IF NOT EXISTS course_discussion_entries (
            id INTEGER PRIMARY KEY,
            target_type VARCHAR NOT NULL,
            target_id INTEGER NOT NULL,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            class_id INTEGER NOT NULL REFERENCES classes(id),
            author_user_id INTEGER NOT NULL REFERENCES users(id),
            body TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_course_discussion_target ON course_discussion_entries(target_type, target_id, subject_id, class_id)",
        "CREATE INDEX IF NOT EXISTS ix_course_discussion_created ON course_discussion_entries(created_at)",
        "ALTER TABLE course_discussion_entries ADD COLUMN IF NOT EXISTS message_kind VARCHAR NOT NULL DEFAULT 'human'",
        "ALTER TABLE course_discussion_entries ADD COLUMN IF NOT EXISTS llm_invocation BOOLEAN NOT NULL DEFAULT FALSE",
        """
        CREATE TABLE IF NOT EXISTS discussion_llm_jobs (
            id INTEGER PRIMARY KEY,
            subject_id INTEGER NOT NULL REFERENCES subjects(id),
            class_id INTEGER NOT NULL REFERENCES classes(id),
            target_type VARCHAR NOT NULL,
            target_id INTEGER NOT NULL,
            requester_user_id INTEGER NOT NULL REFERENCES users(id),
            requester_student_id INTEGER REFERENCES students(id),
            user_entry_id INTEGER NOT NULL REFERENCES course_discussion_entries(id) ON DELETE CASCADE,
            assistant_entry_id INTEGER REFERENCES course_discussion_entries(id) ON DELETE SET NULL,
            status VARCHAR NOT NULL DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
        """,
        "CREATE INDEX IF NOT EXISTS ix_discussion_llm_jobs_subject ON discussion_llm_jobs(subject_id)",
        """
        CREATE TABLE IF NOT EXISTS llm_discussion_quota_reservations (
            id INTEGER PRIMARY KEY,
            job_id INTEGER NOT NULL UNIQUE REFERENCES discussion_llm_jobs(id) ON DELETE CASCADE,
            student_id INTEGER NOT NULL REFERENCES students(id),
            subject_id INTEGER REFERENCES subjects(id),
            usage_date VARCHAR NOT NULL,
            timezone VARCHAR NOT NULL DEFAULT 'UTC',
            reserved_tokens INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS llm_discussion_token_usage_logs (
            id INTEGER PRIMARY KEY,
            job_id INTEGER NOT NULL UNIQUE REFERENCES discussion_llm_jobs(id) ON DELETE CASCADE,
            subject_id INTEGER REFERENCES subjects(id),
            student_id INTEGER NOT NULL REFERENCES students(id),
            usage_date VARCHAR NOT NULL,
            timezone VARCHAR NOT NULL DEFAULT 'UTC',
            input_tokens INTEGER,
            output_tokens INTEGER,
            total_tokens INTEGER,
            billing_note VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
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
        _course_llm_legacy_quota_cols = (
            "daily_student_token_limit",
            "daily_course_token_limit",
            "quota_timezone",
            "estimated_chars_per_token",
            "estimated_image_tokens",
        )
        if engine.dialect.name == "postgresql":
            for _col in _course_llm_legacy_quota_cols:
                connection.execute(text(f"ALTER TABLE course_llm_configs DROP COLUMN IF EXISTS {_col}"))
        else:
            for _col in _course_llm_legacy_quota_cols:
                try:
                    connection.execute(text(f"ALTER TABLE course_llm_configs DROP COLUMN {_col}"))
                except OperationalError:
                    pass

    if engine.dialect.name == "postgresql":
        _ensure_course_llm_endpoint_preset_ondelete_cascade()

    _backfill_default_llm_groups_for_existing_configs()
    _ensure_llm_global_quota_policy_row()
    _ensure_default_llm_endpoint_preset()
    _ensure_llm_assistant_system_user()
    _backfill_course_material_chapters()


def _backfill_course_material_chapters() -> None:
    """Ensure uncategorized chapter per course and link existing materials."""
    db = SessionLocal()
    try:
        for subj in db.query(Subject).all():
            unc = (
                db.query(CourseMaterialChapter)
                .filter(
                    CourseMaterialChapter.subject_id == subj.id,
                    CourseMaterialChapter.is_uncategorized.is_(True),
                )
                .first()
            )
            if not unc:
                unc = CourseMaterialChapter(
                    subject_id=subj.id,
                    parent_id=None,
                    title="未分类",
                    sort_order=0,
                    is_uncategorized=True,
                )
                db.add(unc)
                db.flush()

            mats = (
                db.query(CourseMaterial)
                .filter(CourseMaterial.subject_id == subj.id)
                .order_by(CourseMaterial.created_at.asc())
                .all()
            )
            for idx, mat in enumerate(mats):
                exists = (
                    db.query(CourseMaterialSection)
                    .filter(
                        CourseMaterialSection.material_id == mat.id,
                        CourseMaterialSection.chapter_id == unc.id,
                    )
                    .first()
                )
                if not exists:
                    db.add(
                        CourseMaterialSection(
                            material_id=mat.id,
                            chapter_id=unc.id,
                            sort_order=idx,
                        )
                    )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_default_llm_endpoint_preset() -> None:
    """
    Seed the built-in LLM preset (name = DEFAULT_LLM_PRESET_NAME) when missing so new installs
    match admin UI defaults. Does not overwrite an existing preset of the same name.

    Set DEFAULT_LLM_API_KEY or DEFAULT_LLM_PRESET_API_KEY in the environment to supply the API
    key on first insert (never committed to the repository).
    """
    db = SessionLocal()
    try:
        row = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.name == DEFAULT_LLM_PRESET_NAME).first()
        if row:
            return
        api_key = settings.resolved_default_llm_api_key()
        now = datetime.now(timezone.utc)
        db.add(
            LLMEndpointPreset(
                name=DEFAULT_LLM_PRESET_NAME,
                base_url="https://yunwu.ai/v1",
                api_key=api_key,
                model_name="gpt-5.4",
                connect_timeout_seconds=30,
                read_timeout_seconds=180,
                max_retries=3,
                initial_backoff_seconds=5,
                is_active=True,
                supports_vision=True,
                validation_status="validated",
                validation_message="系统默认端点（首次安装种子）。请在设置中运行连通性校验以刷新状态。",
                text_validation_status="passed",
                text_validation_message=None,
                vision_validation_status="skipped",
                vision_validation_message=None,
                validated_at=now,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_llm_global_quota_policy_row() -> None:
    """Single global policy row (id=1) for LLM daily caps, estimation, and billing calendar timezone."""
    db = SessionLocal()
    try:
        row = db.query(LLMGlobalQuotaPolicy).filter(LLMGlobalQuotaPolicy.id == 1).first()
        if row:
            if getattr(row, "max_parallel_grading_tasks", None) is None:
                row.max_parallel_grading_tasks = 3
            if getattr(row, "estimated_chars_per_token", None) is None:
                row.estimated_chars_per_token = 4.0
            if getattr(row, "estimated_image_tokens", None) is None:
                row.estimated_image_tokens = 850
            db.commit()
            return
        db.add(
            LLMGlobalQuotaPolicy(
                id=1,
                default_daily_student_tokens=100_000,
                quota_timezone="Asia/Shanghai",
                estimated_chars_per_token=4.0,
                estimated_image_tokens=850,
                max_parallel_grading_tasks=3,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_llm_assistant_system_user() -> None:
    """Reserved user for discussion LLM assistant messages (not a login account)."""
    db = SessionLocal()
    try:
        un = "__system_llm_assistant__"
        if db.query(User).filter(User.username == un).first():
            return
        db.add(
            User(
                username=un,
                hashed_password=get_password_hash(os.urandom(16).hex()),
                real_name="智能助教",
                role=UserRole.TEACHER.value,
                is_active=False,
            )
        )
        try:
            db.commit()
        except IntegrityError:
            # Parallel startup or repeated bootstrap can race the unique username insert.
            db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_course_llm_endpoint_preset_ondelete_cascade() -> None:
    """Course endpoint rows disappear when a global preset is deleted (DB-enforced)."""
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE course_llm_config_endpoints DROP CONSTRAINT IF EXISTS course_llm_config_endpoints_preset_id_fkey")
        )
        conn.execute(
            text(
                """
                ALTER TABLE course_llm_config_endpoints
                ADD CONSTRAINT course_llm_config_endpoints_preset_id_fkey
                FOREIGN KEY (preset_id) REFERENCES llm_endpoint_presets(id) ON DELETE CASCADE
                """
            )
        )


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
    ensured_subject_ids: set[int] = set()

    for homework in db.query(Homework).all():
        if homework.subject_id and homework.subject_id not in ensured_subject_ids:
            ensured_subject_ids.add(int(homework.subject_id))
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
            seed_demo_course_bundle(db)
            sync_existing_courses(db)
            backfill_homework_grading_data(db)
            reconcile_student_users_and_roster(db)
            db.commit()
        else:
            reconcile_student_users_and_roster(db)
            db.commit()
            print("INIT_DEFAULT_DATA is false. Table creation completed without seed data.")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap()
