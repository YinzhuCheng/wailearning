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

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import Class, Gender, Student, User, UserRole


@pytest.fixture(autouse=True)
def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates

    ensure_schema_updates()
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "adm").first():
            db.add(
                User(
                    username="adm",
                    hashed_password=get_password_hash("a"),
                    real_name="Admin",
                    role=UserRole.ADMIN.value,
                )
            )
            db.commit()
    finally:
        db.close()
    yield
    SessionLocal().close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    r = client.post("/api/auth/login", data={"username": "adm", "password": "a"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


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
