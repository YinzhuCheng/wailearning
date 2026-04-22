"""
API tests for LLM endpoint presets and course LLM config.

Real LLM calls are avoided by patching ``validate_endpoint_connectivity`` on the
router module (the same object ``validate_preset`` invokes).
"""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, LLMEndpointPreset, Subject, User, UserRole


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


def _login(client: TestClient, username: str, password: str) -> dict[str, str]:
    r = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    db = SessionLocal()
    try:
        db.add(
            User(
                username="admin_test",
                hashed_password=get_password_hash("admin_test_pass"),
                real_name="Admin Test",
                role=UserRole.ADMIN.value,
            )
        )
        db.commit()
    finally:
        db.close()
    return _login(client, "admin_test", "admin_test_pass")


@pytest.fixture
def teacher_course_context(client: TestClient) -> dict:
    """One class, one teacher-owned subject; teacher can manage course LLM config."""
    db = SessionLocal()
    try:
        klass = Class(name="Test Class", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username="teacher_test",
            hashed_password=get_password_hash("teacher_test_pass"),
            real_name="Teacher Test",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        course = Subject(name="Test Course", teacher_id=teacher.id, class_id=klass.id)
        db.add(course)
        db.commit()
        return {"teacher_username": "teacher_test", "teacher_password": "teacher_test_pass", "subject_id": course.id}
    finally:
        db.close()


@pytest.fixture
def teacher_headers(client: TestClient, teacher_course_context: dict) -> dict[str, str]:
    return _login(
        client,
        teacher_course_context["teacher_username"],
        teacher_course_context["teacher_password"],
    )


def test_teacher_can_get_presets_list(client: TestClient, admin_headers, teacher_headers):
    r = client.get("/api/llm-settings/presets", headers=teacher_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_non_admin_cannot_create_preset(client: TestClient, teacher_headers):
    r = client.post(
        "/api/llm-settings/presets",
        headers=teacher_headers,
        json={
            "name": "virtual-openai",
            "base_url": "https://example.invalid/v1/",
            "api_key": "sk-test",
            "model_name": "gpt-test",
        },
    )
    assert r.status_code == 403


def test_admin_create_preset_duplicate_name(client: TestClient, admin_headers):
    body = {
        "name": "virtual-endpoint-a",
        "base_url": "https://api.virtual.test/v1/",
        "api_key": "sk-virtual",
        "model_name": "virtual-model",
    }
    r1 = client.post("/api/llm-settings/presets", headers=admin_headers, json=body)
    assert r1.status_code == 200
    r2 = client.post("/api/llm-settings/presets", headers=admin_headers, json=body)
    assert r2.status_code == 400
    assert "already exists" in r2.json().get("detail", "")


@mock.patch("app.routers.llm_settings.validate_endpoint_connectivity", return_value=(True, "mock ok"))
def test_validate_preset_updates_status(_, client: TestClient, admin_headers):
    create = client.post(
        "/api/llm-settings/presets",
        headers=admin_headers,
        json={
            "name": "virtual-vision-ok",
            "base_url": "https://api.virtual.test/v1/",
            "api_key": "sk-virtual",
            "model_name": "virtual-model",
        },
    )
    assert create.status_code == 200
    preset_id = create.json()["id"]

    val = client.post(f"/api/llm-settings/presets/{preset_id}/validate", headers=admin_headers)
    assert val.status_code == 200
    data = val.json()
    assert data["validation_status"] == "validated"
    assert data["supports_vision"] is True


@mock.patch("app.routers.llm_settings.validate_endpoint_connectivity", return_value=(True, "mock ok"))
def test_teacher_can_attach_validated_preset_to_course(
    _, client: TestClient, admin_headers, teacher_headers, teacher_course_context
):
    create = client.post(
        "/api/llm-settings/presets",
        headers=admin_headers,
        json={
            "name": "virtual-for-course",
            "base_url": "https://api.virtual.test/v1/",
            "api_key": "sk-virtual",
            "model_name": "virtual-model",
        },
    )
    assert create.status_code == 200
    preset_id = create.json()["id"]
    val = client.post(f"/api/llm-settings/presets/{preset_id}/validate", headers=admin_headers)
    assert val.status_code == 200

    subject_id = teacher_course_context["subject_id"]
    get_cfg = client.get(f"/api/llm-settings/courses/{subject_id}", headers=teacher_headers)
    assert get_cfg.status_code == 200

    payload = {
        "is_enabled": True,
        "response_language": "zh",
        "quota_timezone": "UTC",
        "estimated_chars_per_token": 4.0,
        "estimated_image_tokens": 850,
        "max_input_tokens": 16000,
        "max_output_tokens": 1200,
        "endpoints": [{"preset_id": preset_id, "priority": 1}],
    }
    put = client.put(
        f"/api/llm-settings/courses/{subject_id}",
        headers=teacher_headers,
        json=payload,
    )
    assert put.status_code == 200, put.text
    out = put.json()
    assert len(out["endpoints"]) == 1
    assert out["endpoints"][0]["preset_id"] == preset_id


def test_course_update_rejects_unvalidated_preset(
    client: TestClient, admin_headers, teacher_headers, teacher_course_context
):
    """No mock: validate not called; preset stays pending and must not be assignable."""
    db = SessionLocal()
    try:
        p = LLMEndpointPreset(
            name="virtual-pending",
            base_url="https://api.virtual.test/v1/",
            api_key="sk-virtual",
            model_name="virtual-model",
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        preset_id = p.id
    finally:
        db.close()

    subject_id = teacher_course_context["subject_id"]
    payload = {
        "is_enabled": False,
        "quota_timezone": "UTC",
        "estimated_chars_per_token": 4.0,
        "estimated_image_tokens": 850,
        "max_input_tokens": 16000,
        "max_output_tokens": 1200,
        "endpoints": [{"preset_id": preset_id, "priority": 1}],
    }
    put = client.put(
        f"/api/llm-settings/courses/{subject_id}",
        headers=teacher_headers,
        json=payload,
    )
    assert put.status_code == 400
    assert "vision validation" in put.json().get("detail", "").lower()
