"""
行为测试：LLM token 预检与预留、日限额记账、billing_note、课程配额快照、评分材料 manifest。
"""

from __future__ import annotations

import io
import uuid
import zipfile
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.attachments import ATTACHMENTS_DIR
from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.llm_grading import (
    VISION_TEST_IMAGE_DATA_URL,
    MaterialBlock,
    _build_scoring_messages,
    _build_student_material,
    estimate_request_tokens_from_material,
    precheck_quota,
    process_grading_task,
    record_usage_if_needed,
)
from app.main import app
from app.models import (
    Class,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    HomeworkAttempt,
    HomeworkGradingTask,
    LLMEndpointPreset,
    LLMTokenUsageLog,
    Student,
    Subject,
    User,
    UserRole,
)
from tests.llm_scenario import ensure_admin, json_llm_response, login_api, make_grading_course_with_homework


def _tiny_png_bytes() -> bytes:
    import base64

    b64 = VISION_TEST_IMAGE_DATA_URL.split("base64,", 1)[1]
    return base64.b64decode(b64)


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
    yield
    SessionLocal().close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_precheck_quota_distinct_error_student_vs_course():
    db = SessionLocal()
    try:
        cfg = CourseLLMConfig(
            subject_id=42,
            is_enabled=True,
            daily_student_token_limit=1000,
            daily_course_token_limit=1000,
            quota_timezone="UTC",
            max_input_tokens=16000,
            max_output_tokens=1200,
        )
        with mock.patch("app.llm_grading._get_used_tokens_for_scope") as mock_used:

            def used_tokens(db_inner, **kw):
                if kw.get("student_id") is not None:
                    return 950
                if kw.get("subject_id") is not None:
                    return 0
                return 0

            mock_used.side_effect = used_tokens
            ok, code = precheck_quota(db, cfg, student_id=1, subject_id=42, estimated_tokens=100)
            assert ok is False
            assert code == "quota_exceeded_student"

            def used_tokens_course(db_inner, **kw):
                if kw.get("student_id") is not None:
                    return 0
                if kw.get("subject_id") is not None:
                    return 950
                return 0

            mock_used.side_effect = used_tokens_course
            ok2, code2 = precheck_quota(db, cfg, student_id=1, subject_id=42, estimated_tokens=100)
            assert ok2 is False
            assert code2 == "quota_exceeded_course"

            mock_used.side_effect = lambda db_inner, **kw: 0
            ok3, code3 = precheck_quota(db, cfg, student_id=1, subject_id=42, estimated_tokens=100)
            assert ok3 is True
            assert code3 is None
    finally:
        db.close()


def test_grading_task_failed_precheck_student_shows_student_error_code(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(daily_student_token_limit=100)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "answer for quota student"},
    )
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()
    process_grading_task(tid)
    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "failed"
        assert task.error_code == "quota_exceeded_student"
        assert "学生" in (task.error_message or "")
    finally:
        db.close()


def test_grading_task_failed_precheck_course_shows_course_error_code(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(daily_course_token_limit=100)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "answer for quota course"},
    )
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()
    process_grading_task(tid)
    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "failed"
        assert task.error_code == "quota_exceeded_course"
        assert "课程" in (task.error_message or "")
    finally:
        db.close()


def test_usage_log_always_written_after_successful_llm_call(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(daily_student_token_limit=500_000)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "graded once"},
    )
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client, "post", lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(80.0, "ok"))
    ):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        log = db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == tid).first()
        assert log is not None
        assert log.total_tokens == 15
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.billed_total_tokens == 15
    finally:
        db.close()


def test_usage_log_billing_note_when_post_call_exceeds_student_cap():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        klass = Class(name=f"bill_{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"bt_{uid}",
            hashed_password=get_password_hash("p"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        stu_user = User(
            username=f"bs_{uid}",
            hashed_password=get_password_hash("p"),
            real_name="S",
            role=UserRole.STUDENT.value,
            class_id=klass.id,
        )
        db.add(stu_user)
        db.flush()
        stud = Student(name="S", student_no=f"sn_{uid}", class_id=klass.id)
        db.add(stud)
        db.flush()
        course = Subject(name=f"sub_{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=True,
            daily_student_token_limit=1000,
            quota_timezone="UTC",
            max_input_tokens=16000,
            max_output_tokens=1200,
        )
        db.add(cfg)
        db.flush()
        preset = LLMEndpointPreset(
            name=f"pr_{uid}",
            base_url="https://x.test/v1/",
            api_key="k",
            model_name="m",
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(preset)
        db.flush()
        db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=preset.id, priority=1))
        hw = Homework(
            title="hw",
            content="c",
            class_id=klass.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.flush()
        att = HomeworkAttempt(
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            class_id=klass.id,
            content="x",
        )
        db.add(att)
        db.flush()
        old_task = HomeworkGradingTask(
            attempt_id=att.id,
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            status="success",
        )
        db.add(old_task)
        db.flush()
        from app.llm_grading import _get_usage_date

        usage_date = _get_usage_date("UTC")
        db.add(
            LLMTokenUsageLog(
                task_id=old_task.id,
                subject_id=course.id,
                student_id=stud.id,
                usage_date=usage_date,
                timezone="UTC",
                total_tokens=950,
            )
        )
        new_task = HomeworkGradingTask(
            attempt_id=att.id,
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            status="processing",
        )
        db.add(new_task)
        db.commit()
        record_usage_if_needed(db, new_task, cfg, {"prompt_tokens": 100, "completion_tokens": 100, "total_tokens": 200})
        db.commit()
        log = db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == new_task.id).first()
        assert log is not None
        assert log.billing_note and "over_daily_limit" in log.billing_note
        assert "student" in log.billing_note
    finally:
        db.close()


def test_usage_log_billing_note_when_post_call_exceeds_course_cap():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        klass = Class(name=f"bc_{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"btc_{uid}",
            hashed_password=get_password_hash("p"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        stud = Student(name="S2", student_no=f"sn2_{uid}", class_id=klass.id)
        db.add(stud)
        db.flush()
        course = Subject(name=f"sub2_{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=True,
            daily_course_token_limit=1000,
            quota_timezone="UTC",
            max_input_tokens=16000,
            max_output_tokens=1200,
        )
        db.add(cfg)
        db.flush()
        preset = LLMEndpointPreset(
            name=f"pr2_{uid}",
            base_url="https://x2.test/v1/",
            api_key="k",
            model_name="m",
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(preset)
        db.flush()
        db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=preset.id, priority=1))
        hw = Homework(
            title="hw2",
            content="c",
            class_id=klass.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.flush()
        att = HomeworkAttempt(
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            class_id=klass.id,
            content="x",
        )
        db.add(att)
        db.flush()
        old_task = HomeworkGradingTask(
            attempt_id=att.id,
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            status="success",
        )
        db.add(old_task)
        db.flush()
        from app.llm_grading import _get_usage_date

        usage_date = _get_usage_date("UTC")
        db.add(
            LLMTokenUsageLog(
                task_id=old_task.id,
                subject_id=course.id,
                student_id=stud.id,
                usage_date=usage_date,
                timezone="UTC",
                total_tokens=950,
            )
        )
        new_task = HomeworkGradingTask(
            attempt_id=att.id,
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            status="processing",
        )
        db.add(new_task)
        db.commit()
        record_usage_if_needed(db, new_task, cfg, {"total_tokens": 200})
        db.commit()
        log = db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == new_task.id).first()
        assert log is not None
        assert log.billing_note and "over_daily_limit" in log.billing_note
        assert "course" in log.billing_note
    finally:
        db.close()


@mock.patch("app.routers.llm_settings.validate_vision_connectivity", return_value=(True, "vision ok"))
@mock.patch("app.routers.llm_settings.validate_text_connectivity", return_value=(True, "text ok"))
def test_get_course_llm_config_includes_quota_usage_shape(_, __, client: TestClient):
    db = SessionLocal()
    try:
        klass = Class(name="QuotaClass", grade=2026)
        db.add(klass)
        db.flush()
        admin = User(
            username="quota_admin",
            hashed_password=get_password_hash("quota_admin_pass"),
            real_name="A",
            role=UserRole.ADMIN.value,
        )
        db.add(admin)
        db.flush()
        teacher = User(
            username="quota_teacher",
            hashed_password=get_password_hash("quota_teacher_pass"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name="QuotaCourse", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        db.commit()
        sid = course.id
    finally:
        db.close()

    admin_h = login_api(client, "quota_admin", "quota_admin_pass")
    teacher_h = login_api(client, "quota_teacher", "quota_teacher_pass")
    c = client.post(
        "/api/llm-settings/presets",
        headers=admin_h,
        json={"name": "quota-preset", "base_url": "https://a.test/v1/", "api_key": "k", "model_name": "m"},
    )
    assert c.status_code == 200, c.text
    pid = c.json()["id"]
    client.post(
        f"/api/llm-settings/presets/{pid}/validate",
        headers=admin_h,
        files={"image": ("t.png", _tiny_png_bytes(), "image/png")},
    )
    put = client.put(
        f"/api/llm-settings/courses/{sid}",
        headers=teacher_h,
        json={
            "is_enabled": True,
            "quota_timezone": "UTC",
            "daily_course_token_limit": 5000,
            "estimated_chars_per_token": 4.0,
            "estimated_image_tokens": 850,
            "max_input_tokens": 8000,
            "max_output_tokens": 1000,
            "endpoints": [{"preset_id": pid, "priority": 1}],
        },
    )
    assert put.status_code == 200, put.text
    g = client.get(f"/api/llm-settings/courses/{sid}", headers=teacher_h)
    assert g.status_code == 200
    qu = g.json().get("quota_usage") or {}
    assert qu.get("usage_date")
    assert qu.get("quota_timezone") == "UTC"
    assert qu.get("daily_course_token_limit") == 5000
    assert qu.get("course_used_tokens_today") is not None
    assert qu.get("course_remaining_tokens_today") is not None


@mock.patch("app.routers.llm_settings.validate_vision_connectivity", return_value=(True, "vision ok"))
@mock.patch("app.routers.llm_settings.validate_text_connectivity", return_value=(True, "text ok"))
def test_get_course_llm_config_quota_usage_null_without_course_limit(_, __, client: TestClient):
    db = SessionLocal()
    try:
        klass = Class(name="QuotaClass2", grade=2026)
        db.add(klass)
        db.flush()
        admin = User(
            username="quota_admin2",
            hashed_password=get_password_hash("p2"),
            real_name="A",
            role=UserRole.ADMIN.value,
        )
        db.add(admin)
        db.flush()
        teacher = User(
            username="quota_teacher2",
            hashed_password=get_password_hash("p2"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name="QuotaCourse2", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.commit()
        sid = course.id
    finally:
        db.close()

    admin_h = login_api(client, "quota_admin2", "p2")
    teacher_h = login_api(client, "quota_teacher2", "p2")
    c = client.post(
        "/api/llm-settings/presets",
        headers=admin_h,
        json={"name": "quota-preset-2", "base_url": "https://a.test/v1/", "api_key": "k", "model_name": "m"},
    )
    pid = c.json()["id"]
    client.post(
        f"/api/llm-settings/presets/{pid}/validate",
        headers=admin_h,
        files={"image": ("t.png", _tiny_png_bytes(), "image/png")},
    )
    client.put(
        f"/api/llm-settings/courses/{sid}",
        headers=teacher_h,
        json={
            "is_enabled": True,
            "quota_timezone": "UTC",
            "estimated_chars_per_token": 4.0,
            "estimated_image_tokens": 850,
            "max_input_tokens": 8000,
            "max_output_tokens": 1000,
            "endpoints": [{"preset_id": pid, "priority": 1}],
        },
    )
    g = client.get(f"/api/llm-settings/courses/{sid}", headers=teacher_h)
    qu = g.json().get("quota_usage") or {}
    assert qu.get("course_used_tokens_today") is None
    assert qu.get("course_remaining_tokens_today") is None


def test_estimate_request_tokens_grows_with_large_data_url_payload():
    db = SessionLocal()
    try:
        cfg = CourseLLMConfig(
            subject_id=1,
            is_enabled=True,
            estimated_chars_per_token=4.0,
            estimated_image_tokens=850,
            max_input_tokens=16000,
            max_output_tokens=100,
            quota_timezone="UTC",
        )
        small_url = "data:image/png;base64," + "a" * 40
        large_url = "data:image/png;base64," + "b" * 4000
        m_small = {"student_blocks": [MaterialBlock(1, "i", "image", image_data_url=small_url)], "notes_text": ""}
        m_large = {"student_blocks": [MaterialBlock(1, "i", "image", image_data_url=large_url)], "notes_text": ""}
        a = estimate_request_tokens_from_material(
            cfg,
            m_small,
            assignment_text="A",
            teacher_prompt="",
            student_intro="",
        )
        b = estimate_request_tokens_from_material(
            cfg,
            m_large,
            assignment_text="A",
            teacher_prompt="",
            student_intro="",
        )
        assert b >= a
    finally:
        db.close()


def test_artifact_manifest_includes_block_metadata_after_material_build():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        klass = Class(name=f"am_{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"amt_{uid}",
            hashed_password=get_password_hash("p"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name=f"amc_{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=True,
            max_input_tokens=16000,
            max_output_tokens=1200,
            quota_timezone="UTC",
        )
        db.add(cfg)
        db.flush()
        hw = Homework(
            title="manifest hw",
            content="do it",
            class_id=klass.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.flush()
        stud = Student(name="St", student_no=f"st_{uid}", class_id=klass.id)
        db.add(stud)
        db.flush()
        att = HomeworkAttempt(
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            class_id=klass.id,
            content="my submission text",
        )
        db.add(att)
        db.commit()
        db.refresh(hw)
        db.refresh(att)
        material = _build_student_material(db, hw, att, cfg)
        inc = (material.get("artifact_manifest") or {}).get("included") or []
        assert len(inc) >= 1
        row = inc[0]
        for key in ("path", "type", "logical_path", "mime_hint", "origin", "truncated"):
            assert key in row
    finally:
        db.close()


def test_scoring_messages_have_distinct_sections_for_instructor_and_submission():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        klass = Class(name=f"sm_{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"smt_{uid}",
            hashed_password=get_password_hash("p"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name=f"smc_{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=True,
            teacher_prompt="extra hint",
            max_input_tokens=16000,
            max_output_tokens=1200,
            quota_timezone="UTC",
        )
        db.add(cfg)
        db.flush()
        hw = Homework(
            title="sm hw",
            content="instruction body",
            class_id=klass.id,
            subject_id=course.id,
            max_score=10,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.flush()
        stud = Student(name="S", student_no=f"sms_{uid}", class_id=klass.id)
        db.add(stud)
        db.flush()
        att = HomeworkAttempt(
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            class_id=klass.id,
            content="hello",
            is_late=False,
        )
        db.add(att)
        db.commit()
        db.refresh(hw)
        db.refresh(att)
        material = _build_student_material(db, hw, att, cfg)
        msgs = _build_scoring_messages(hw, att, cfg, material)
        assert msgs[0]["role"] == "system"
        user_content = msgs[1]["content"]
        texts = [p["text"] for p in user_content if p.get("type") == "text"]
        joined = "\n".join(texts)
        assert "教师侧作业说明与材料" in joined
        assert "提交元数据" in joined
        assert "教师补充提示" in joined
    finally:
        db.close()


def test_zip_attachment_skipped_reason_propagates_to_notes_or_manifest():
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:8]
        klass = Class(name=f"zip_{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"zip_t_{uid}",
            hashed_password=get_password_hash("p"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name=f"zip_c_{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=True,
            max_input_tokens=16000,
            max_output_tokens=1200,
            quota_timezone="UTC",
        )
        db.add(cfg)
        db.flush()
        hw = Homework(
            title="zip hw",
            content="read zip",
            class_id=klass.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.flush()
        stud = Student(name="Z", student_no=f"z_{uid}", class_id=klass.id)
        db.add(stud)
        db.flush()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("a.txt", "one")
            zf.writestr("b.txt", "two")
        buf.seek(0)
        ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
        stored = f"{uuid.uuid4().hex}.zip"
        disk_path = ATTACHMENTS_DIR / stored
        disk_path.write_bytes(buf.getvalue())
        att_url = f"/uploads/attachments/{stored}"
        att = HomeworkAttempt(
            homework_id=hw.id,
            student_id=stud.id,
            subject_id=course.id,
            class_id=klass.id,
            content="see zip",
            attachment_name="pack.zip",
            attachment_url=att_url,
        )
        db.add(att)
        db.commit()
        db.refresh(hw)
        db.refresh(att)
        with mock.patch("app.llm_grading.MAX_ZIP_FILES", 1):
            material = _build_student_material(db, hw, att, cfg)
        skipped = (material.get("artifact_manifest") or {}).get("skipped") or []
        assert any("超出展开文件数" in (s.get("reason") or "") for s in skipped)
        notes = material.get("notes_text") or ""
        assert "未纳入内容" in notes or "超出展开文件数" in notes
    finally:
        db.close()
