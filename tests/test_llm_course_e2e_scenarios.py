"""
Fifteen end-to-end style API scenarios covering:
  INIT_LLM bootstrap bundle, rubric visibility, course cover + permissions,
  LLM capabilities / assistant gate + chat, course LLM group payloads,
  auto-grading prerequisites, global LLM fallback for grading,
  class-teacher homework creation, and grading prompt material labels.

Uses FastAPI TestClient + SQLite (see tests/conftest.py). External LLM HTTP is mocked.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.bootstrap import (
    DEMO_SEED_COURSE_NAME,
    DEMO_SEED_HOMEWORK_TITLE,
    seed_initial_llm_deployment_bundle,
)
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.llm_grading import _build_student_material, process_grading_task
from app.main import app
from app.models import (
    Class,
    CourseEnrollment,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    HomeworkAttempt,
    HomeworkGradingTask,
    HomeworkSubmission,
    LLMEndpointPreset,
    LLMGroup,
    Semester,
    Student,
    Subject,
    User,
    UserRole,
)
from tests.llm_scenario import json_llm_response, login_api, make_grading_course_with_homework


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


@pytest.fixture(autouse=True)
def _mock_preset_connectivity():
    with (
        mock.patch(
            "app.routers.llm_settings.validate_text_connectivity",
            return_value=(True, "text ok"),
        ),
        mock.patch(
            "app.routers.llm_settings.validate_vision_connectivity",
            return_value=(True, "vision ok"),
        ),
    ):
        yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _make_admin(client: TestClient, username: str = "admin", password: str = "adminpw") -> dict[str, str]:
    db = SessionLocal()
    try:
        db.add(
            User(
                username=username,
                hashed_password=get_password_hash(password),
                real_name="Admin",
                role=UserRole.ADMIN.value,
            )
        )
        db.commit()
    finally:
        db.close()
    return login_api(client, username, password)


def _preset_payload(name: str) -> dict:
    return {
        "name": name,
        "base_url": "https://api.e2e.test/v1/",
        "api_key": "sk-e2e",
        "model_name": "e2e-model",
    }


def test_init_llm_deployment_bundle_seeds_demo_course_and_submissions(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "INIT_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(settings, "INIT_LLM_API_KEY", "k")
    monkeypatch.setattr(settings, "INIT_LLM_BASE_URL", "https://init.test/v1/")
    monkeypatch.setattr(settings, "INIT_LLM_MODEL_NAME", "m")
    monkeypatch.setattr(settings, "INIT_LLM_PRESET_NAME", "init-preset-e2e")

    db = SessionLocal()
    try:
        db.add(
            User(
                username="admin",
                hashed_password=get_password_hash("x"),
                real_name="Admin",
                role=UserRole.ADMIN.value,
            )
        )
        db.add(Semester(name="2026-e2e", year=2026, is_active=True))
        db.commit()
    finally:
        db.close()

    with (
        mock.patch("app.bootstrap.validate_text_connectivity", return_value=(True, "ok")),
        mock.patch("app.bootstrap.validate_vision_connectivity", return_value=(True, "vision ok")),
    ):
        db = SessionLocal()
        try:
            seed_initial_llm_deployment_bundle(db)
        finally:
            db.close()

    db = SessionLocal()
    try:
        preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.name == "init-preset-e2e").first()
        assert preset is not None
        assert preset.validation_status == "validated"
        assert preset.supports_vision is True
        course = db.query(Subject).filter(Subject.name == DEMO_SEED_COURSE_NAME).first()
        assert course is not None
        hw = db.query(Homework).filter(Homework.title == DEMO_SEED_HOMEWORK_TITLE).first()
        assert hw is not None
        assert hw.auto_grading_enabled is True
        subs = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == hw.id).all()
        assert len(subs) >= 2
        cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == course.id).first()
        assert cfg is not None and cfg.is_enabled is True
    finally:
        db.close()


def test_student_homework_list_hides_teacher_rubric_and_reference(client: TestClient):
    ctx = make_grading_course_with_homework()
    db = SessionLocal()
    try:
        hw = db.query(Homework).filter(Homework.id == ctx["homework_id"]).first()
        hw.rubric_text = "visible to students"
        hw.rubric_teacher_text = "teacher only rubric"
        hw.reference_answer = "teacher only ref"
        db.commit()
    finally:
        db.close()

    stu_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.get(
        "/api/homeworks",
        headers=stu_h,
        params={"class_id": ctx.get("class_id") or _class_id_for_homework(ctx["homework_id"]), "subject_id": ctx["subject_id"]},
    )
    assert r.status_code == 200, r.text
    row = next((x for x in r.json()["data"] if x["id"] == ctx["homework_id"]), None)
    assert row is not None
    assert row["rubric_text"] == "visible to students"
    assert row.get("rubric_teacher_text") is None
    assert row.get("reference_answer") is None

    teach_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    r2 = client.get(
        "/api/homeworks",
        headers=teach_h,
        params={"subject_id": ctx["subject_id"]},
    )
    assert r2.status_code == 200
    row2 = next((x for x in r2.json()["data"] if x["id"] == ctx["homework_id"]), None)
    assert row2["rubric_teacher_text"] == "teacher only rubric"
    assert row2["reference_answer"] == "teacher only ref"


def _class_id_for_homework(homework_id: int) -> int:
    db = SessionLocal()
    try:
        return db.query(Homework).filter(Homework.id == homework_id).first().class_id
    finally:
        db.close()


def test_teacher_can_update_course_cover_image_url(client: TestClient):
    ctx = make_grading_course_with_homework()
    teach_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    url = "https://cdn.example/cover-teacher.png"
    r = client.put(f"/api/subjects/{ctx['subject_id']}", headers=teach_h, json={"cover_image_url": url})
    assert r.status_code == 200, r.text
    assert r.json()["cover_image_url"] == url


def test_admin_overwrites_teacher_cover_last_write_wins(client: TestClient):
    ctx = make_grading_course_with_homework()
    teach_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    admin_h = _make_admin(client, "root", "rpw")
    assert client.put(
        f"/api/subjects/{ctx['subject_id']}",
        headers=teach_h,
        json={"cover_image_url": "https://a.test/1.png"},
    ).status_code == 200
    assert client.put(
        f"/api/subjects/{ctx['subject_id']}",
        headers=admin_h,
        json={"cover_image_url": "https://b.test/2.png"},
    ).status_code == 200
    g = client.get(f"/api/subjects/{ctx['subject_id']}", headers=teach_h)
    assert g.json()["cover_image_url"] == "https://b.test/2.png"


def test_capabilities_track_global_validated_preset(client: TestClient):
    ctx = make_grading_course_with_homework()
    stu_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r_ok = client.get("/api/llm-settings/capabilities", headers=stu_h)
    assert r_ok.status_code == 200
    assert r_ok.json()["has_validated_vision_preset"] is True

    db = SessionLocal()
    try:
        for p in db.query(LLMEndpointPreset).all():
            p.validation_status = "pending"
            p.supports_vision = False
        db.commit()
    finally:
        db.close()

    r_empty = client.get("/api/llm-settings/capabilities", headers=stu_h)
    assert r_empty.status_code == 200
    assert r_empty.json()["has_validated_vision_preset"] is False


def test_create_homework_auto_grading_rejects_without_validated_llm(client: TestClient):
    uid = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        klass = Class(name=f"c-{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"th_{uid}",
            hashed_password=get_password_hash("tp"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name=f"sub-{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        db.add(
            CourseLLMConfig(
                subject_id=course.id,
                is_enabled=True,
                max_input_tokens=8000,
                max_output_tokens=1000,
                quota_timezone="UTC",
            )
        )
        db.commit()
        sid = course.id
        cid = klass.id
    finally:
        db.close()

    teach_h = login_api(client, f"th_{uid}", "tp")
    due = datetime.now(timezone.utc) + timedelta(days=3)
    r = client.post(
        "/api/homeworks",
        headers=teach_h,
        json={
            "title": "hw",
            "content": "x",
            "class_id": cid,
            "subject_id": sid,
            "due_date": due.isoformat(),
            "auto_grading_enabled": True,
        },
    )
    assert r.status_code == 400
    assert "NO_VALIDATED_LLM" in r.json().get("detail", "") or "LLM" in r.json().get("detail", "")


def test_create_homework_auto_grading_rejects_when_course_llm_disabled(client: TestClient):
    ctx = make_grading_course_with_homework(course_llm_enabled=False)
    teach_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    due = datetime.now(timezone.utc) + timedelta(days=3)
    r = client.post(
        "/api/homeworks",
        headers=teach_h,
        json={
            "title": "hw2",
            "content": "x",
            "class_id": _class_id_for_homework(ctx["homework_id"]),
            "subject_id": ctx["subject_id"],
            "due_date": due.isoformat(),
            "auto_grading_enabled": True,
        },
    )
    assert r.status_code == 400
    assert "COURSE_LLM_NOT_ENABLED" in r.json().get("detail", "")


def test_course_llm_groups_payload_roundtrip(client: TestClient):
    admin_h = _make_admin(client, "adm", "apw")
    ctx = make_grading_course_with_homework()
    teach_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    p1 = client.post("/api/llm-settings/presets", headers=admin_h, json=_preset_payload("g-p1")).json()["id"]
    p2 = client.post("/api/llm-settings/presets", headers=admin_h, json=_preset_payload("g-p2")).json()["id"]

    body = {
        "is_enabled": True,
        "response_language": "zh-CN",
        "quota_timezone": "UTC",
        "estimated_chars_per_token": 4.0,
        "estimated_image_tokens": 850,
        "max_input_tokens": 8000,
        "max_output_tokens": 1000,
        "groups": [
            {"priority": 1, "name": "primary", "members": [{"preset_id": p1, "priority": 1}]},
            {"priority": 2, "name": "backup", "members": [{"preset_id": p2, "priority": 1}]},
        ],
        "endpoints": [],
    }
    put = client.put(f"/api/llm-settings/courses/{ctx['subject_id']}", headers=teach_h, json=body)
    assert put.status_code == 200, put.text
    got = client.get(f"/api/llm-settings/courses/{ctx['subject_id']}", headers=teach_h).json()
    assert len(got["groups"]) == 2
    names = {g["name"] for g in got["groups"]}
    assert names == {"primary", "backup"}
    assert got.get("uses_course_endpoint_routing", True) is True


def test_assistant_availability_blocked_without_validated_llm(client: TestClient):
    uid = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        klass = Class(name=f"as-{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"ast_{uid}",
            hashed_password=get_password_hash("tp"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        stu_u = User(
            username=f"astu_{uid}",
            hashed_password=get_password_hash("sp"),
            real_name="S",
            role=UserRole.STUDENT.value,
            class_id=klass.id,
        )
        db.add(stu_u)
        db.flush()
        st = Student(name="S", student_no=f"astu_{uid}", class_id=klass.id)
        db.add(st)
        db.flush()
        course = Subject(name=f"asub-{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        db.add(
            CourseEnrollment(subject_id=course.id, student_id=st.id, class_id=klass.id, enrollment_type="required")
        )
        db.add(
            CourseLLMConfig(
                subject_id=course.id,
                is_enabled=True,
                max_input_tokens=8000,
                max_output_tokens=1000,
                quota_timezone="UTC",
            )
        )
        db.commit()
        sid = course.id
    finally:
        db.close()

    stu_h = login_api(client, f"astu_{uid}", "sp")
    r = client.get(f"/api/llm-settings/courses/{sid}/assistant/availability", headers=stu_h)
    assert r.status_code == 200
    assert r.json()["can_chat"] is False
    assert r.json()["reason_code"] == "NO_VALIDATED_LLM_IN_SYSTEM"


def test_assistant_availability_blocked_when_course_llm_disabled(client: TestClient):
    ctx = make_grading_course_with_homework(course_llm_enabled=False)
    stu_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.get(f"/api/llm-settings/courses/{ctx['subject_id']}/assistant/availability", headers=stu_h)
    assert r.status_code == 200
    assert r.json()["can_chat"] is False
    assert r.json()["reason_code"] == "COURSE_LLM_NOT_ENABLED"


def test_assistant_chat_returns_reply_with_mocked_http(client: TestClient):
    ctx = make_grading_course_with_homework()
    stu_h = login_api(client, ctx["student_username"], ctx["student_password"])

    with mock.patch(
        "app.routers.llm_settings.run_course_assistant_turn",
        return_value="助教回复：你好",
    ):
        r = client.post(
            f"/api/llm-settings/courses/{ctx['subject_id']}/assistant/chat",
            headers=stu_h,
            json={"message": "你好"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("reply")
    assert "助教回复" in data["reply"]


def test_grading_uses_global_fallback_when_course_has_no_endpoint_rows(client: TestClient):
    ctx = make_grading_course_with_homework()
    db = SessionLocal()
    try:
        cfg = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == ctx["subject_id"]).first()
        db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == cfg.id).delete()
        db.query(LLMGroup).filter(LLMGroup.config_id == cfg.id).delete()
        db.commit()
    finally:
        db.close()

    client_b = TestClient(app)
    stu_h = login_api(client_b, ctx["student_username"], ctx["student_password"])
    r = client_b.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=stu_h,
        json={"content": "fallback path answer"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first()
        assert task is not None
        tid = task.id
    finally:
        db.close()

    def fake_post(self, url, **kwargs):
        return httpx.Response(200, json=json_llm_response(77.0, "fb ok"))

    with mock.patch.object(httpx.Client, "post", fake_post):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task.status == "success"
    finally:
        db.close()


def test_class_teacher_can_create_homework_with_auto_grading(client: TestClient):
    uid = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        klass = Class(name=f"ct-{uid}", grade=2026)
        db.add(klass)
        db.flush()
        instructor = User(
            username=f"ins_{uid}",
            hashed_password=get_password_hash("ip"),
            real_name="Ins",
            role=UserRole.TEACHER.value,
        )
        db.add(instructor)
        db.flush()
        ct = User(
            username=f"ct_{uid}",
            hashed_password=get_password_hash("cp"),
            real_name="CT",
            role=UserRole.CLASS_TEACHER.value,
            class_id=klass.id,
        )
        db.add(ct)
        db.flush()
        course = Subject(name=f"ctc-{uid}", teacher_id=instructor.id, class_id=klass.id)
        db.add(course)
        db.flush()
        preset = LLMEndpointPreset(
            name=f"ct-p-{uid}",
            base_url="https://ct.test/v1/",
            api_key="k",
            model_name="m",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(preset)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=course.id,
            is_enabled=True,
            max_input_tokens=8000,
            max_output_tokens=1000,
            quota_timezone="UTC",
        )
        db.add(cfg)
        db.flush()
        db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=preset.id, priority=1))
        db.commit()
        sid = course.id
        cid = klass.id
    finally:
        db.close()

    ct_h = login_api(client, f"ct_{uid}", "cp")
    due = datetime.now(timezone.utc) + timedelta(days=2)
    r = client.post(
        "/api/homeworks",
        headers=ct_h,
        json={
            "title": "ct hw",
            "content": "do",
            "class_id": cid,
            "subject_id": sid,
            "due_date": due.isoformat(),
            "auto_grading_enabled": True,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["auto_grading_enabled"] is True


def test_build_student_material_contains_visibility_section_labels():
    hw = Homework(
        title="t",
        content="c",
        class_id=1,
        subject_id=1,
        max_score=100,
        rubric_text="r1",
        rubric_teacher_text="r2",
        reference_answer="ans",
    )
    att = HomeworkAttempt(
        homework_id=1,
        student_id=1,
        subject_id=1,
        class_id=1,
        content="s",
    )
    cfg = CourseLLMConfig(subject_id=1, max_input_tokens=16000, max_output_tokens=800, quota_timezone="UTC")
    material = _build_student_material(hw, att, cfg)
    blob = "\n".join(material["assignment_texts"])
    assert "【对学生可见的评分要点】" in blob
    assert "【仅教师可见的评分要点】" in blob
    assert "【参考答案或思路】" in blob


def test_enable_auto_grading_after_course_llm_turned_on(client: TestClient):
    ctx = make_grading_course_with_homework(course_llm_enabled=False)
    teach_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    due = datetime.now(timezone.utc) + timedelta(days=5)
    cr = client.post(
        "/api/homeworks",
        headers=teach_h,
        json={
            "title": "toggle hw",
            "content": "x",
            "class_id": _class_id_for_homework(ctx["homework_id"]),
            "subject_id": ctx["subject_id"],
            "due_date": due.isoformat(),
            "auto_grading_enabled": False,
        },
    )
    assert cr.status_code == 200
    hid = cr.json()["id"]

    bad = client.put(f"/api/homeworks/{hid}", headers=teach_h, json={"auto_grading_enabled": True})
    assert bad.status_code == 400

    pid = ctx["preset_id"]
    ok_cfg = client.put(
        f"/api/llm-settings/courses/{ctx['subject_id']}",
        headers=teach_h,
        json={
            "is_enabled": True,
            "quota_timezone": "UTC",
            "estimated_chars_per_token": 4.0,
            "estimated_image_tokens": 850,
            "max_input_tokens": 16000,
            "max_output_tokens": 1200,
            "endpoints": [{"preset_id": pid, "priority": 1}],
        },
    )
    assert ok_cfg.status_code == 200, ok_cfg.text

    good = client.put(f"/api/homeworks/{hid}", headers=teach_h, json={"auto_grading_enabled": True})
    assert good.status_code == 200
    assert good.json()["auto_grading_enabled"] is True
