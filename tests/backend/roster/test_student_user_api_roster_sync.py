"""
高难度 API 集成：管理员「用户管理」与花名册（Student）的双向一致性。

覆盖：
- POST /api/users 创建学生账号后，花名册自动出现且 display name 对齐；随后 sync_student_user_from_roster_row
  应使 User.real_name 与花名册一致（若仅从 roster 创建则验证双向）；
- PUT /api/users 修改学生 real_name 后，sync_student_roster_from_user_accounts 应把同名花名册行的姓名同步更新；
- POST /api/students 省略 gender 时 schema 默认 male；
- POST /api/students/batch 行对象省略 gender 键时按「男」解析并成功入库。
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import Class, Gender, Student, User
from tests.scenarios.llm_scenario import ensure_admin, login_api


@pytest.fixture(autouse=True)
def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates

    ensure_schema_updates()
    try:
        ensure_admin()
    except IntegrityError:
        db = SessionLocal()
        try:
            db.rollback()
        finally:
            db.close()
    yield
    SessionLocal().close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    return login_api(client, "pytest_admin", "pytest_admin_pass")


def test_admin_create_student_user_creates_roster_and_round_trips_display_name(client: TestClient):
    """创建学生用户 → 花名册行存在且学号一致；花名册姓名应与用户姓名一致。"""
    suf = uuid.uuid4().hex[:8]
    uname = f"stu_api_{suf}"
    db = SessionLocal()
    try:
        k = Class(name=f"API同步班_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    h = _admin_headers(client)
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": uname,
            "password": "init-pass",
            "real_name": "展示姓名甲",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    uid = r.json()["id"]

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.student_no == uname, Student.class_id == kid).first()
        assert st is not None
        assert st.name == "展示姓名甲"
        u = db.query(User).filter(User.id == uid).first()
        assert u.real_name == "展示姓名甲"
    finally:
        db.close()

    student_login = client.post("/api/auth/login", data={"username": uname, "password": "init-pass"})
    assert student_login.status_code == 200, student_login.text
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    quota = client.get("/api/llm-settings/courses/student-quotas", headers=student_headers)
    assert quota.status_code == 200, quota.text
    assert quota.json().get("daily_student_token_limit") is not None

    r2 = client.put(
        f"/api/users/{uid}",
        headers=h,
        json={"real_name": "展示姓名乙"},
    )
    assert r2.status_code == 200, r.text

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.student_no == uname, Student.class_id == kid).first()
        assert st is not None
        assert st.name == "展示姓名乙"
    finally:
        db.close()


def test_admin_create_student_user_then_roster_name_change_via_put_keeps_single_row(client: TestClient):
    """改名后仍只有一行花名册（防误建新行）；学号不变。"""
    suf = uuid.uuid4().hex[:8]
    uname = f"stu_one_{suf}"
    db = SessionLocal()
    try:
        k = Class(name=f"单行班_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    h = _admin_headers(client)
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": uname,
            "password": "p",
            "real_name": "V1",
            "role": "student",
            "class_id": kid,
        },
    )
    assert r.status_code == 200
    uid = r.json()["id"]

    client.put(f"/api/users/{uid}", headers=h, json={"real_name": "V2"})
    client.put(f"/api/users/{uid}", headers=h, json={"real_name": "V3"})

    db = SessionLocal()
    try:
        rows = db.query(Student).filter(Student.student_no == uname, Student.class_id == kid).all()
        assert len(rows) == 1
        assert rows[0].name == "V3"
    finally:
        db.close()


def test_post_students_omit_gender_defaults_to_male(client: TestClient):
    h = _admin_headers(client)
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        k = Class(name=f"缺省性别班_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/api/students",
        headers=h,
        json={
            "name": "无性别字段",
            "student_no": f"nog_{suf}",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    assert r.json().get("gender") == "male"

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.student_no == f"nog_{suf}").first()
        assert st is not None
        assert st.gender == Gender.MALE
    finally:
        db.close()

    student_login = client.post("/api/auth/login", data={"username": f"nog_{suf}", "password": f"nog_{suf}"})
    assert student_login.status_code == 200, student_login.text
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    quota = client.get("/api/llm-settings/courses/student-quotas", headers=student_headers)
    assert quota.status_code == 200, quota.text
    assert quota.json().get("daily_student_token_limit") is not None


def test_post_students_without_student_no_generates_bound_student_account(client: TestClient):
    h = _admin_headers(client)
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        k = Class(name=f"AutoNo_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/api/students",
        headers=h,
        json={
            "name": "Auto Number",
            "gender": "male",
            "class_id": kid,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["student_no"].startswith("SYS")
    assert body["has_user"] is True

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.id == body["id"]).one()
        u = db.query(User).filter(User.student_id == st.id).one()
        assert u.role == "student"
        assert u.username == st.student_no
        assert u.class_id == kid
    finally:
        db.close()


def test_admin_can_create_unassigned_student_then_assign_class(client: TestClient):
    h = _admin_headers(client)
    suf = uuid.uuid4().hex[:8]

    r = client.post(
        "/api/students",
        headers=h,
        json={
            "name": "Unassigned Student",
            "gender": "male",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["class_id"] is None
    assert body["class_name"] is None
    assert body["student_no"].startswith("SYS")
    assert body["has_user"] is True

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == body["id"]).one()
        user = db.query(User).filter(User.student_id == student.id).one()
        klass = Class(name=f"AssignLater_{suf}", grade=2026)
        db.add(klass)
        db.flush()
        sid = student.id
        kid = klass.id
        assert student.class_id is None
        assert user.class_id is None
        db.commit()
    finally:
        db.close()

    listed = client.get("/api/students", headers=h, params={"page": 1, "page_size": 1000})
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]
    assert any(row["id"] == sid and row["class_id"] is None for row in rows)

    moved = client.put(
        f"/api/students/{sid}",
        headers=h,
        json={"class_id": kid},
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["class_id"] == kid

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.id == sid).one()
        user = db.query(User).filter(User.student_id == sid).one()
        assert student.class_id == kid
        assert user.class_id == kid
    finally:
        db.close()


def test_teacher_cannot_create_unassigned_student(client: TestClient):
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        klass = Class(name=f"TeacherNoUnassigned_{suf}", grade=2026)
        db.add(klass)
        db.flush()
        teacher = User(
            username=f"teacher_no_unassigned_{suf}",
            hashed_password=get_password_hash("teacher-pass"),
            real_name="Teacher",
            role="teacher",
            class_id=None,
        )
        db.add(teacher)
        db.commit()
    finally:
        db.close()

    headers = login_api(client, f"teacher_no_unassigned_{suf}", "teacher-pass")
    r = client.post(
        "/api/students",
        headers=headers,
        json={"name": "No Class", "gender": "male"},
    )
    assert r.status_code == 403


def test_create_student_user_can_bind_existing_student_id_without_username_student_no_match(client: TestClient):
    h = _admin_headers(client)
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        k = Class(name=f"BindExisting_{suf}", grade=2026)
        db.add(k)
        db.flush()
        st = Student(
            name="Canonical Student",
            student_no=f"real_no_{suf}",
            gender=Gender.MALE,
            class_id=k.id,
        )
        db.add(st)
        db.flush()
        kid = k.id
        sid = st.id
        db.commit()
    finally:
        db.close()

    username = f"login_only_{suf}"
    r = client.post(
        "/api/users",
        headers=h,
        json={
            "username": username,
            "password": "p",
            "real_name": "Canonical Student",
            "role": "student",
            "student_id": sid,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["student_id"] == sid
    assert body["class_id"] == kid

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.id == sid).one()
        u = db.query(User).filter(User.username == username).one()
        assert u.student_id == sid
        assert u.class_id == kid
        assert st.student_no == f"real_no_{suf}"
    finally:
        db.close()


def test_batch_students_row_without_gender_key_succeeds_as_male(client: TestClient):
    h = _admin_headers(client)
    suf = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        k = Class(name=f"批量缺省_{suf}", grade=2026)
        db.add(k)
        db.flush()
        kid = k.id
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/api/students/batch",
        headers=h,
        json={
            "students": [
                {"name": "批量甲", "student_no": f"b1_{suf}", "class_id": kid},
            ]
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["success"] == 1

    db = SessionLocal()
    try:
        st = db.query(Student).filter(Student.student_no == f"b1_{suf}").first()
        assert st.gender == Gender.MALE
    finally:
        db.close()
