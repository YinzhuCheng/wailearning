"""
LLM 组级路由与连通性分阶段：使用 httpx mock，不访问外网。

覆盖：多组优先级、组内多成员 failover、先文本后整体验证、artifact 中 llm_routing。
"""

from __future__ import annotations

from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.llm_grading import process_grading_task, validate_text_connectivity, validate_vision_connectivity
from app.main import app
from app.models import (
    Class,
    CourseEnrollment,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    LLMEndpointPreset,
    LLMGroup,
    Student,
    Subject,
    User,
    UserRole,
)
from tests.llm_scenario import ensure_admin, json_llm_response, login_api


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


def _make_grouped_course_with_homework() -> dict:
    uid = "g1"
    db = SessionLocal()
    try:
        klass = Class(name=f"g-class-{uid}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username="g_teach",
            hashed_password=get_password_hash("g_tp"),
            real_name="G T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        stu = User(
            username="g_stu",
            hashed_password=get_password_hash("g_sp"),
            real_name="G S",
            role=UserRole.STUDENT.value,
            class_id=klass.id,
        )
        db.add(stu)
        db.flush()
        stud = Student(name="G S", student_no="g_stu", class_id=klass.id)
        db.add(stud)
        db.flush()
        course = Subject(name=f"g-subj-{uid}", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.flush()
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=stud.id,
                class_id=klass.id,
                enrollment_type="required",
            )
        )
        p1 = LLMEndpointPreset(
            name="preset_g1",
            base_url="https://g1.test/v1/",
            api_key="k1",
            model_name="m1",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        p2 = LLMEndpointPreset(
            name="preset_g2",
            base_url="https://g2.test/v1/",
            api_key="k2",
            model_name="m2",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        p3 = LLMEndpointPreset(
            name="preset_g3",
            base_url="https://g3.test/v1/",
            api_key="k3",
            model_name="m3",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add_all([p1, p2, p3])
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
        g1 = LLMGroup(config_id=cfg.id, priority=1, name="primary")
        g2 = LLMGroup(config_id=cfg.id, priority=2, name="secondary")
        db.add_all([g1, g2])
        db.flush()
        db.add(
            CourseLLMConfigEndpoint(
                config_id=cfg.id,
                group_id=g1.id,
                preset_id=p1.id,
                priority=1,
            )
        )
        db.add(
            CourseLLMConfigEndpoint(
                config_id=cfg.id,
                group_id=g2.id,
                preset_id=p2.id,
                priority=1,
            )
        )
        db.add(
            CourseLLMConfigEndpoint(
                config_id=cfg.id,
                group_id=g2.id,
                preset_id=p3.id,
                priority=2,
            )
        )
        hw = Homework(
            title="g-hw",
            content="c",
            class_id=klass.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.commit()
        db.refresh(hw)
        return {
            "homework_id": hw.id,
            "p1": p1.id,
            "p2": p2.id,
            "p3": p3.id,
            "student_headers": None,
        }
    finally:
        db.close()


def test_validate_text_and_vision_helpers():
    with mock.patch.object(httpx.Client, "post", return_value=httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]})):
        ok, _ = validate_text_connectivity("https://a.test/v1/", "k", "m", 5, 10)
        assert ok
        ok2, _ = validate_vision_connectivity("https://a.test/v1/", "k", "m", 5, 10)
        assert ok2


def test_two_groups_failover_to_second_group(client: TestClient):
    """第一组 401 后进入第二组；第二组第一个 500 后第二个 200 成功。"""
    ensure_admin()
    ctx = _make_grouped_course_with_homework()
    ctx["student_headers"] = login_api(client, "g_stu", "g_sp")
    client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=ctx["student_headers"],
        json={"content": "answer"},
    )
    from app.models import HomeworkGradingTask

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).one().id
    finally:
        db.close()

    calls: list[str] = []

    def fake_post(self, url, **kwargs):
        b = (kwargs.get("json") or {}).get("body")
        if isinstance(b, str):
            payload = {}
        else:
            payload = kwargs.get("json") or {}
        model = payload.get("model") or ""
        calls.append(model)
        if model == "m1":
            return httpx.Response(401, json={"error": "nope"})
        if model == "m2":
            return httpx.Response(500, json={"error": "u"})
        if model == "m3":
            return httpx.Response(200, json=json_llm_response(77.0, "from m3"))
        return httpx.Response(500, json={})

    with mock.patch.object(httpx.Client, "post", fake_post):
        process_grading_task(tid)

    assert calls[0] == "m1"
    assert "m2" in calls
    assert calls[-1] == "m3"
    db = SessionLocal()
    try:
        from app.models import HomeworkGradingTask, HomeworkSubmission, HomeworkScoreCandidate

        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).one()
        assert task.status == "success"
        sub = db.query(HomeworkSubmission).one()
        assert sub.review_score == 77.0
        auto = db.query(HomeworkScoreCandidate).filter(HomeworkScoreCandidate.source == "auto").one()
        assert auto.source_metadata.get("endpoint_id") == ctx["p3"]
        m = task.artifact_manifest or {}
        assert m.get("llm_routing", {}).get("status") == "ok"
    finally:
        db.close()


def test_put_course_config_with_groups_payload(client: TestClient):
    ensure_admin()
    admin_h = login_api(client, "pytest_admin", "pytest_admin_pass")
    c = client.post(
        "/api/llm-settings/presets",
        headers=admin_h,
        json={"name": "g-api-p", "base_url": "https://x.test/v1/", "api_key": "k", "model_name": "m"},
    )
    pid = c.json()["id"]
    db = SessionLocal()
    try:
        k = Class(name="ApiClass", grade=2026)
        db.add(k)
        db.flush()
        t = User(
            username="g_put_t",
            hashed_password=get_password_hash("x"),
            real_name="G Put T",
            role=UserRole.TEACHER.value,
        )
        db.add(t)
        db.flush()
        s = Subject(name="ApiSubj", teacher_id=t.id, class_id=k.id)
        db.add(s)
        db.commit()
        sid = s.id
    finally:
        db.close()
    p2r = client.post(
        "/api/llm-settings/presets",
        headers=admin_h,
        json={"name": "g-api-p2", "base_url": "https://x2.test/v1/", "api_key": "k2", "model_name": "m2"},
    )
    p2 = p2r.json()["id"]
    db = SessionLocal()
    try:
        for preset_id in (pid, p2):
            pr = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == preset_id).first()
            if pr:
                pr.validation_status = "validated"
                pr.supports_vision = True
        db.commit()
    finally:
        db.close()
    th = login_api(client, "g_put_t", "x")
    r = client.put(
        f"/api/llm-settings/courses/{sid}",
        headers=th,
        json={
            "is_enabled": True,
            "quota_timezone": "UTC",
            "estimated_chars_per_token": 4.0,
            "estimated_image_tokens": 100,
            "max_input_tokens": 8000,
            "max_output_tokens": 500,
            "groups": [
                {
                    "priority": 1,
                    "name": "G1",
                    "members": [{"preset_id": pid, "priority": 1}],
                },
                {
                    "priority": 2,
                    "name": "G2",
                    "members": [
                        {"preset_id": p2, "priority": 1},
                    ],
                },
            ],
        },
    )
    assert r.status_code == 200, r.text
    g = r.json()["groups"]
    assert len(g) == 2
    assert len(g[0]["members"]) == 1
    assert g[0]["members"][0]["preset_id"] == pid


def test_validate_endpoint_order_text_before_vision():
    """validate_endpoint_connectivity：先发纯文本请求，再发多模态请求。"""
    from app import llm_grading

    received: list[str] = []

    def fake_post(self, url, **kwargs):
        payload = kwargs.get("json") or {}
        msgs = (payload.get("messages") or [{}])[0]
        ctn = msgs.get("content")
        if isinstance(ctn, str):
            received.append("text")
        else:
            received.append("vision")
        return httpx.Response(200, json={"choices": [{"message": {"content": "OK"}}]})

    with mock.patch.object(httpx.Client, "post", fake_post):
        ok, _ = llm_grading.validate_endpoint_connectivity("https://ord.test/v1/", "k", "m", 5, 20)
    assert ok
    assert received == ["text", "vision"]
