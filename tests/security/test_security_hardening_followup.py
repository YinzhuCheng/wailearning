"""Focused security hardening follow-up tests.

These cases complement ``test_security_regression.py`` by exercising lifecycle,
dual-gate, subject-scoped, and attachment ACL edges that are easy to miss in a
small point-in-time security smoke.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.backend.courseeval_backend.api.schemas import UserRole
from apps.backend.courseeval_backend.core.auth import get_password_hash
from apps.backend.courseeval_backend.core.config import Settings, settings
from apps.backend.courseeval_backend.db.database import SessionLocal
from apps.backend.courseeval_backend.db.models import Class, CourseMaterial, User
from tests.scenarios.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


def _bearer_value(headers: dict[str, str]) -> str:
    return headers["Authorization"].split(" ", 1)[1]


def _create_class_teacher() -> dict[str, object]:
    db = SessionLocal()
    try:
        klass = Class(name="security-class-teacher-class", grade=2026)
        db.add(klass)
        db.flush()
        user = User(
            username="security_class_teacher",
            hashed_password=get_password_hash("class_teacher_pass"),
            real_name="Security Class Teacher",
            role=UserRole.CLASS_TEACHER.value,
            class_id=klass.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return {"user_id": user.id, "class_id": klass.id, "username": user.username, "password": "class_teacher_pass"}
    finally:
        db.close()


def test_hard01_change_password_invalidates_existing_token(client: TestClient):
    ctx = make_grading_course_with_homework()
    old_headers = login_api(client, ctx["student_username"], ctx["student_password"])
    new_password = "ChangedPass123!"

    r = client.post(
        "/api/auth/change-password",
        headers=old_headers,
        json={
            "current_password": ctx["student_password"],
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert r.status_code == 200, r.text
    assert client.get("/api/auth/me", headers=old_headers).status_code == 401
    assert client.post("/api/auth/login", data={"username": ctx["student_username"], "password": new_password}).status_code == 200


def test_hard02_admin_reset_password_invalidates_existing_token(client: TestClient):
    ctx = make_grading_course_with_homework()
    ensure_admin()
    student_headers = login_api(client, ctx["student_username"], ctx["student_password"])
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")

    r = client.post(
        f"/api/users/{ctx['student_user_id']}/reset-password",
        headers=admin_headers,
        json={"new_password": "ResetPass123!"},
    )
    assert r.status_code == 200, r.text
    assert client.get("/api/auth/me", headers=student_headers).status_code == 401
    assert client.post("/api/auth/login", data={"username": ctx["student_username"], "password": "ResetPass123!"}).status_code == 200


def test_hard03_inactive_user_token_cannot_access_active_route(client: TestClient):
    ctx = make_grading_course_with_homework()
    ensure_admin()
    student_headers = login_api(client, ctx["student_username"], ctx["student_password"])
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")

    r = client.put(f"/api/users/{ctx['student_user_id']}", headers=admin_headers, json={"is_active": False})
    assert r.status_code == 200, r.text
    assert client.get("/api/auth/me", headers=student_headers).status_code == 400


def test_hard04_e2e_powerful_route_rejects_missing_seed_token(client: TestClient):
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "hardening-seed"
    settings.E2E_DEV_REQUIRE_ADMIN_JWT = False

    r = client.post("/api/e2e/dev/mock-llm/configure", json={"profiles": {}})
    assert r.status_code == 403


def test_hard05_e2e_powerful_route_requires_admin_bearer_when_configured(client: TestClient):
    ctx = make_grading_course_with_homework()
    ensure_admin()
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "hardening-seed"
    settings.E2E_DEV_REQUIRE_ADMIN_JWT = True
    seed = {"X-E2E-Seed-Token": "hardening-seed"}

    assert client.post("/api/e2e/dev/mock-llm/configure", headers=seed, json={"profiles": {}}).status_code == 403

    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    r_teacher = client.post(
        "/api/e2e/dev/mock-llm/configure",
        headers={**seed, **teacher_headers},
        json={"profiles": {}},
    )
    assert r_teacher.status_code == 403

    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    r_admin = client.post(
        "/api/e2e/dev/mock-llm/configure",
        headers={**seed, **admin_headers},
        json={"profiles": {}},
    )
    assert r_admin.status_code == 200, r_admin.text


def test_hard06_reset_scenario_remains_seed_only_under_admin_jwt_mode(client: TestClient):
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "hardening-seed"
    settings.E2E_DEV_REQUIRE_ADMIN_JWT = True

    r = client.post("/api/e2e/dev/reset-scenario", headers={"X-E2E-Seed-Token": "hardening-seed"})
    assert r.status_code == 200, r.text
    assert r.json()["admin"]["username"]


def test_hard07_student_cannot_patch_own_role_or_class(client: TestClient):
    ctx = make_grading_course_with_homework()
    student_headers = login_api(client, ctx["student_username"], ctx["student_password"])

    r = client.put(
        f"/api/users/{ctx['student_user_id']}",
        headers=student_headers,
        json={"role": UserRole.ADMIN.value, "class_id": None},
    )
    assert r.status_code == 403


def test_hard08_non_admin_self_update_cannot_deactivate_account(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.put(f"/api/users/{ctx['teacher_id']}", headers=teacher_headers, json={"is_active": False})
    assert r.status_code == 200, r.text
    assert r.json()["is_active"] is True


def test_hard09_teacher_owned_subject_attendance_write_does_not_require_teacher_class_id(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.post(
        "/api/attendance",
        headers=teacher_headers,
        json={
            "student_id": ctx["student_id"],
            "class_id": ctx["class_id"],
            "subject_id": ctx["subject_id"],
            "date": "2026-05-12",
            "status": "present",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["subject_id"] == ctx["subject_id"]


def test_hard10_foreign_teacher_cannot_write_attendance_for_other_course(client: TestClient):
    ctx_a = make_grading_course_with_homework()
    ctx_b = make_grading_course_with_homework()
    foreign_headers = login_api(client, ctx_b["teacher_username"], ctx_b["teacher_password"])

    r = client.post(
        "/api/attendance",
        headers=foreign_headers,
        json={
            "student_id": ctx_a["student_id"],
            "class_id": ctx_a["class_id"],
            "subject_id": ctx_a["subject_id"],
            "date": "2026-05-12",
            "status": "present",
        },
    )
    assert r.status_code in (403, 404)


def test_hard11_attachment_download_path_traversal_like_name_returns_not_found(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.get("/api/files/download/../../.env", headers=teacher_headers)
    assert r.status_code == 404


def test_hard12_attachment_acl_uses_logical_course_scope_not_just_file_possession(client: TestClient):
    ctx = make_grading_course_with_homework()
    other = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    other_headers = login_api(client, other["teacher_username"], other["teacher_password"])

    upload = client.post(
        "/api/files/upload",
        headers=teacher_headers,
        files={"file": ("acl-proof.txt", b"course scoped attachment", "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    attachment_url = upload.json()["attachment_url"]

    db = SessionLocal()
    try:
        material = CourseMaterial(
            title="ACL proof",
            content="attached",
            attachment_name="acl-proof.txt",
            attachment_url=attachment_url,
            class_id=ctx["class_id"],
            subject_id=ctx["subject_id"],
            created_by=ctx["teacher_id"],
        )
        db.add(material)
        db.commit()
    finally:
        db.close()

    own = client.get("/api/files/download", headers=teacher_headers, params={"attachment_url": attachment_url})
    assert own.status_code == 200, own.text
    foreign = client.get("/api/files/download", headers=other_headers, params={"attachment_url": attachment_url})
    assert foreign.status_code == 403


def test_hard13_require_strong_secrets_rejects_default_secret_outside_production():
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            APP_ENV="development",
            REQUIRE_STRONG_SECRETS=True,
            SECRET_KEY="change-me-in-production",
            DATABASE_URL="postgresql://courseeval:strong-pass@127.0.0.1:5432/courseeval_test",
        )


def test_hard14_production_rejects_default_database_placeholder_even_with_strong_secret():
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings(
            APP_ENV="production",
            E2E_DEV_SEED_ENABLED=False,
            SECRET_KEY="x" * 40,
            DATABASE_URL="postgresql://courseeval:change-me@127.0.0.1:5432/courseeval",
        )


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/e2e/dev/grading-state", None),
        ("POST", "/api/e2e/dev/worker", {"action": "status"}),
        ("POST", "/api/e2e/dev/process-grading", {"max_tasks": 1}),
        ("POST", "/api/e2e/dev/mark-preset-validated", {"preset_id": 1}),
    ],
)
def test_hard15_powerful_e2e_dev_routes_reject_seed_only_when_admin_jwt_required(
    client: TestClient,
    method: str,
    path: str,
    body: dict[str, object] | None,
):
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "hardening-seed"
    settings.E2E_DEV_REQUIRE_ADMIN_JWT = True
    response = client.request(method, path, headers={"X-E2E-Seed-Token": "hardening-seed"}, json=body)
    assert response.status_code == 403
    assert "administrator Bearer" in response.text


def test_hard16_teacher_cannot_assign_new_course_to_another_teacher(client: TestClient):
    ctx = make_grading_course_with_homework()
    other = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.post(
        "/api/subjects",
        headers=teacher_headers,
        json={
            "name": "teacher ownership hardening",
            "teacher_id": other["teacher_id"],
            "class_id": ctx["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["teacher_id"] == ctx["teacher_id"]


def test_hard17_class_teacher_cannot_create_required_course_for_foreign_class(client: TestClient):
    ct = _create_class_teacher()
    db = SessionLocal()
    try:
        foreign_class = Class(name="security-foreign-class", grade=2026)
        db.add(foreign_class)
        db.commit()
        foreign_class_id = foreign_class.id
    finally:
        db.close()

    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))
    r = client.post(
        "/api/subjects",
        headers=ct_headers,
        json={
            "name": "foreign class hardening",
            "class_id": foreign_class_id,
            "course_type": "required",
            "status": "active",
        },
    )
    assert r.status_code in (400, 403)


def test_hard18_encoded_attachment_traversal_like_name_returns_not_found(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.get("/api/files/download/%2e%2e%2f.env", headers=teacher_headers)
    assert r.status_code == 404


def test_hard19_executable_upload_is_rejected_even_for_authenticated_teacher(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.post(
        "/api/files/upload",
        headers=teacher_headers,
        files={"file": ("payload.exe", b"MZ fake executable", "application/x-msdownload")},
    )
    assert r.status_code == 400


def test_hard20_teacher_cannot_browse_student_only_course_catalog(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.get("/api/subjects/course-catalog", headers=teacher_headers)
    assert r.status_code == 403
