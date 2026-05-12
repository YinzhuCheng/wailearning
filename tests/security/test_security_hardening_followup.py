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
from apps.backend.courseeval_backend.db.models import Class, CourseEnrollment, CourseMaterial, Student, SubjectClassLink, User
from tests.scenarios.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


def _bearer_value(headers: dict[str, str]) -> str:
    return headers["Authorization"].split(" ", 1)[1]


def _create_class_teacher(label: str = "class_teacher") -> dict[str, object]:
    db = SessionLocal()
    try:
        klass = Class(name=f"security-{label}-class", grade=2026)
        db.add(klass)
        db.flush()
        user = User(
            username=f"security_{label}",
            hashed_password=get_password_hash(f"{label}_pass123"),
            real_name=f"Security {label}",
            role=UserRole.CLASS_TEACHER.value,
            class_id=klass.id,
            is_active=True,
        )
        db.add(user)
        db.commit()
        return {"user_id": user.id, "class_id": klass.id, "username": user.username, "password": f"{label}_pass123"}
    finally:
        db.close()


def _create_class(name: str) -> int:
    db = SessionLocal()
    try:
        klass = Class(name=name, grade=2026)
        db.add(klass)
        db.commit()
        return int(klass.id)
    finally:
        db.close()


def _linked_class_ids(subject_id: int) -> set[int]:
    db = SessionLocal()
    try:
        return {
            int(row[0])
            for row in db.query(SubjectClassLink.class_id)
            .filter(SubjectClassLink.subject_id == subject_id)
            .all()
        }
    finally:
        db.close()


def _extra_student_for_class(class_id: int, label: str) -> int:
    db = SessionLocal()
    try:
        user = User(
            username=f"security_student_{label}",
            hashed_password=get_password_hash(f"{label}_pass123"),
            real_name=f"Security Student {label}",
            role=UserRole.STUDENT.value,
            class_id=class_id,
            is_active=True,
        )
        db.add(user)
        db.flush()
        student = Student(name=f"Security Student {label}", student_no=user.username, class_id=class_id)
        db.add(student)
        db.flush()
        user.student_id = student.id
        db.commit()
        return int(student.id)
    finally:
        db.close()


def _enrollment_exists(subject_id: int, student_id: int) -> bool:
    db = SessionLocal()
    try:
        return (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.subject_id == subject_id, CourseEnrollment.student_id == student_id)
            .first()
            is not None
        )
    finally:
        db.close()


def _material_count_for_subject(subject_id: int) -> int:
    db = SessionLocal()
    try:
        return db.query(CourseMaterial).filter(CourseMaterial.subject_id == subject_id).count()
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


def test_hard21_class_teacher_cannot_update_required_course_to_foreign_class_id(client: TestClient):
    ct = _create_class_teacher("ct_update_foreign")
    foreign_class_id = _create_class("security-ct-update-foreign")
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))
    created = client.post(
        "/api/subjects",
        headers=ct_headers,
        json={
            "name": "ct owned update foreign class",
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]

    r = client.put(f"/api/subjects/{subject_id}", headers=ct_headers, json={"class_id": foreign_class_id})
    assert r.status_code == 403
    assert _linked_class_ids(subject_id) == {int(ct["class_id"])}


def test_hard22_class_teacher_cannot_update_required_course_with_foreign_class_links(client: TestClient):
    ct = _create_class_teacher("ct_update_links")
    foreign_class_id = _create_class("security-ct-update-link-foreign")
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))
    created = client.post(
        "/api/subjects",
        headers=ct_headers,
        json={
            "name": "ct owned update class links",
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]

    r = client.put(
        f"/api/subjects/{subject_id}",
        headers=ct_headers,
        json={
            "class_links": [
                {"class_id": ct["class_id"], "enrollment_mode": "all_in_class"},
                {"class_id": foreign_class_id, "enrollment_mode": "all_in_class"},
            ]
        },
    )
    assert r.status_code == 403
    assert _linked_class_ids(subject_id) == {int(ct["class_id"])}


def test_hard23_class_teacher_cannot_convert_class_bound_required_course_to_elective(client: TestClient):
    ct = _create_class_teacher("ct_update_elective")
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))
    created = client.post(
        "/api/subjects",
        headers=ct_headers,
        json={
            "name": "ct owned convert elective",
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]

    r = client.put(f"/api/subjects/{subject_id}", headers=ct_headers, json={"course_type": "elective"})
    assert r.status_code == 403
    detail = client.get(f"/api/subjects/{subject_id}", headers=ct_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["course_type"] == "required"
    assert _linked_class_ids(subject_id) == {int(ct["class_id"])}


def test_hard24_class_teacher_cannot_update_foreign_teacher_course_even_with_own_class_link(client: TestClient):
    ct = _create_class_teacher("ct_foreign_teacher")
    ctx = make_grading_course_with_homework()
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "foreign teacher own class linked",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.put(
        f"/api/subjects/{created.json()['id']}",
        headers=ct_headers,
        json={"name": "ct should not mutate teacher-owned course"},
    )
    assert r.status_code == 403


def test_hard25_e2e_dev_reset_wrong_bearer_still_rejects_when_seed_is_valid(client: TestClient):
    ensure_admin()
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "hardening-seed"
    settings.E2E_DEV_REQUIRE_ADMIN_JWT = True

    r = client.post(
        "/api/e2e/dev/mock-llm/configure",
        headers={"X-E2E-Seed-Token": "hardening-seed", "Authorization": "Bearer definitely.invalid.token"},
        json={"profiles": {}},
    )
    assert r.status_code in (401, 403)


def test_hard26_production_rejects_e2e_seed_even_with_strong_secret_and_database_url():
    with pytest.raises(ValueError, match="E2E_DEV_SEED_ENABLED"):
        Settings(
            APP_ENV="production",
            E2E_DEV_SEED_ENABLED=True,
            SECRET_KEY="x" * 40,
            DATABASE_URL="postgresql://courseeval:strong-pass@127.0.0.1:5432/courseeval_prod",
        )


def test_hard27_attachment_duplicate_db_references_with_same_basename_still_enforce_url_acl(client: TestClient):
    ctx = make_grading_course_with_homework()
    other = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    other_headers = login_api(client, other["teacher_username"], other["teacher_password"])

    first = client.post(
        "/api/files/upload",
        headers=teacher_headers,
        files={"file": ("collision-a.txt", b"first collision body", "text/plain")},
    )
    assert first.status_code == 200, first.text
    first_url = first.json()["attachment_url"]
    basename = first_url.rsplit("/", 1)[-1]

    db = SessionLocal()
    try:
        db.add_all(
            [
                CourseMaterial(
                    title="ACL collision first",
                    content="attached",
                    attachment_name="collision-a.txt",
                    attachment_url=first_url,
                    class_id=ctx["class_id"],
                    subject_id=ctx["subject_id"],
                    created_by=ctx["teacher_id"],
                ),
                CourseMaterial(
                    title="ACL collision second same basename",
                    content="attached",
                    attachment_name="collision-b.txt",
                    attachment_url=first_url,
                    class_id=other["class_id"],
                    subject_id=other["subject_id"],
                    created_by=other["teacher_id"],
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    ambiguous = client.get(f"/api/files/download/{basename}", headers=teacher_headers)
    assert ambiguous.status_code == 200, ambiguous.text

    exact = client.get(
        f"/api/files/download/{basename}",
        headers=teacher_headers,
        params={"attachment_url": first_url},
    )
    assert exact.status_code == 200, exact.text

    foreign = client.get(
        f"/api/files/download/{basename}",
        headers=other_headers,
        params={"attachment_url": first_url},
    )
    assert foreign.status_code == 403


def test_hard28_upload_rejects_disguised_executable_content_with_safe_extension(client: TestClient):
    ctx = make_grading_course_with_homework()
    teacher_headers = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    r = client.post(
        "/api/files/upload",
        headers=teacher_headers,
        files={"file": ("payload.txt", b"MZ disguised executable", "text/plain")},
    )
    assert r.status_code == 400


def test_hard29_class_teacher_cannot_delete_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_delete_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible delete guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    assert client.get(f"/api/subjects/{subject_id}", headers=ct_headers).status_code == 200
    r = client.delete(f"/api/subjects/{subject_id}", headers=ct_headers)
    assert r.status_code == 403
    assert client.get(f"/api/subjects/{subject_id}", headers=admin_headers).status_code == 200


def test_hard30_class_teacher_cannot_upload_cover_to_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_cover_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible cover guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.post(
        f"/api/subjects/{subject_id}/cover-image",
        headers=ct_headers,
        files={"file": ("cover.png", b"\x89PNG\r\n\x1a\n", "image/png")},
    )
    assert r.status_code == 403
    detail = client.get(f"/api/subjects/{subject_id}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    assert not detail.json().get("cover_image_url")


def test_hard31_class_teacher_cannot_sync_teacher_owned_visible_course_enrollments(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_sync_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible sync guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.post(f"/api/subjects/{created.json()['id']}/sync-enrollments", headers=ct_headers)
    assert r.status_code == 403


def test_hard32_class_teacher_cannot_roster_enroll_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_roster_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible roster guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    student_id = _extra_student_for_class(int(ct["class_id"]), "ct_roster_visible")
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.post(f"/api/subjects/{subject_id}/roster-enroll", headers=ct_headers, json={"student_ids": [student_id]})
    assert r.status_code == 403
    assert not _enrollment_exists(subject_id, student_id)


def test_hard33_class_teacher_cannot_change_enrollment_type_on_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_enroll_type_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible enrollment type guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    student_id = _extra_student_for_class(int(ct["class_id"]), "ct_enroll_type_visible")
    assert client.post(f"/api/subjects/{subject_id}/sync-enrollments", headers=admin_headers).status_code == 200
    assert _enrollment_exists(subject_id, student_id)
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.put(
        f"/api/subjects/{subject_id}/students/{student_id}/enrollment-type",
        headers=ct_headers,
        json={"enrollment_type": "elective"},
    )
    assert r.status_code == 403


def test_hard34_class_teacher_cannot_remove_student_from_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_remove_student_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible remove student guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    student_id = _extra_student_for_class(int(ct["class_id"]), "ct_remove_student_visible")
    assert client.post(f"/api/subjects/{subject_id}/sync-enrollments", headers=admin_headers).status_code == 200
    assert _enrollment_exists(subject_id, student_id)
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.delete(f"/api/subjects/{subject_id}/students/{student_id}", headers=ct_headers)
    assert r.status_code == 403
    assert _enrollment_exists(subject_id, student_id)


def test_hard35_class_teacher_cannot_create_material_in_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_material_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible material guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    subject_id = created.json()["id"]
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    before = _material_count_for_subject(subject_id)
    r = client.post(
        "/api/materials",
        headers=ct_headers,
        json={
            "title": "ct forbidden material",
            "content": "should not publish",
            "content_format": "plain",
            "class_id": ct["class_id"],
            "subject_id": subject_id,
        },
    )
    assert r.status_code == 403
    assert _material_count_for_subject(subject_id) == before


def test_hard36_class_teacher_cannot_create_homework_in_teacher_owned_visible_course(client: TestClient):
    ctx = make_grading_course_with_homework()
    ct = _create_class_teacher("ct_homework_visible")
    ensure_admin()
    admin_headers = login_api(client, "pytest_admin", "pytest_admin_pass")
    created = client.post(
        "/api/subjects",
        headers=admin_headers,
        json={
            "name": "ct visible homework guard",
            "teacher_id": ctx["teacher_id"],
            "class_id": ct["class_id"],
            "course_type": "required",
            "status": "active",
        },
    )
    assert created.status_code == 200, created.text
    ct_headers = login_api(client, str(ct["username"]), str(ct["password"]))

    r = client.post(
        "/api/homeworks",
        headers=ct_headers,
        json={
            "title": "ct forbidden homework",
            "content": "should not assign",
            "content_format": "plain",
            "class_id": ct["class_id"],
            "subject_id": created.json()["id"],
            "due_date": None,
            "max_score": 100,
            "grade_precision": "integer",
            "auto_grading_enabled": False,
            "allow_late_submission": True,
            "late_submission_affects_score": False,
            "max_submissions": None,
            "llm_routing_spec": None,
        },
    )
    assert r.status_code == 403
