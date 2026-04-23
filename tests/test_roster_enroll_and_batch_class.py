"""
花名册进课（POST /api/subjects/{id}/roster-enroll）与管理员批量调班（POST /api/users/batch-set-class）。

## 已实现（本文件内 active tests）
- roster-enroll：仅本班花名册学生可写入；外班 / 不存在 ID 计入 skipped；已在课计入 skipped；第二次部分成功。
- batch-set-class：管理员将学生用户调到目标班后，User.class_id 与同学号 Student.class_id 一致。

## API 扩展规格（下一轮实现：下方 test_* 占位已 pytest.skip）

### POST …/roster-enroll
| # | 场景 | Given | When | Then |
|---|------|--------|------|------|
| R1 | 学生禁止 | 学生 JWT | POST roster-enroll | 403 |
| R2 | 无关教师禁止 | 另一任课教师 JWT（无该课权限） | POST | 403 |
| R3 | 退选后恢复并清 block | 本班学生曾被 DELETE …/students/{id} 退选，存在 CourseEnrollmentBlock，无 CourseEnrollment | 任课教师 POST roster-enroll 含该 student_id | 200；选课行存在；block 行删除；可选：作业提交由 403 恢复为 200（与 test_student_course_roster_behavior 对齐） |
| R4 | 选修课类型 | course.course_type = elective | roster-enroll 一名本班生 | CourseEnrollment.enrollment_type == elective 且 can_remove True |
| R5 | 课程无班级 | Subject.class_id IS NULL | POST | 400 |
| R6 | 空 student_ids | 合法教师 | POST {"student_ids":[]} | 200；各计数为 0 |

### POST …/batch-set-class
| # | 场景 | Given | When | Then |
|---|------|--------|------|------|
| B1 | 非管理员禁止 | 教师 JWT | POST batch-set-class | 403 |
| B2 | 混合 user_ids | 同一请求含学生用户 + 教师用户 ID | 管理员 POST | updated 仅学生；errors 含教师项 reason |
| B3 | 无效 class_id | class_id 不存在 | 管理员 POST | 400 |
| B4 | 幂等同班 | 学生 user.class_id 已是目标班 | 管理员 POST | updated == 0；库中 class_id 不变 |
| B5 | 花名册与账号曾不一致 | User.class_id 与 Student(student_no=user.username).class_id 不同 | 管理员 batch-set-class 到目标班 | 二者均变为目标班；prepare 后选课与 test_admin_user_class_change 行为一致 |

## UI → 后端全链路（E2E，下一轮）
自动化使用 Playwright，规格写在 frontend/e2e/roster-and-users.spec.ts 顶部注释；默认整包 skip，见该文件。与上表 R/B 编号做追溯矩阵即可。
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, CourseEnrollment, Gender, Student, Subject, User, UserRole

_ROUND2 = "Round 2: implement per module docstring (API table R1–R6, B1–B5)"


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


def _seed_teacher_course(client: TestClient):
    suffix = "re_batch"
    db = SessionLocal()
    try:
        klass = Class(name=f"花名册班_{suffix}", grade=2026)
        db.add(klass)
        db.flush()
        t = User(
            username=f"t_{suffix}",
            hashed_password=get_password_hash("tp"),
            real_name="任课",
            role=UserRole.TEACHER.value,
        )
        db.add(t)
        db.flush()
        s1 = Student(
            name="甲",
            student_no=f"sn1_{suffix}",
            gender=Gender.MALE,
            class_id=klass.id,
        )
        s2 = Student(
            name="乙",
            student_no=f"sn2_{suffix}",
            gender=Gender.FEMALE,
            class_id=klass.id,
        )
        other = Class(name=f"外班_{suffix}", grade=2026)
        db.add(other)
        db.flush()
        s_other = Student(
            name="外班生",
            student_no=f"snx_{suffix}",
            gender=Gender.MALE,
            class_id=other.id,
        )
        db.add_all([s1, s2, s_other])
        db.flush()
        course = Subject(
            name=f"课_{suffix}",
            teacher_id=t.id,
            class_id=klass.id,
            course_type="required",
            status="active",
        )
        db.add(course)
        db.flush()
        cid = course.id
        ids = (s1.id, s2.id, s_other.id, klass.id, t.username)
        db.commit()
    finally:
        db.close()
    th = {"Authorization": f"Bearer {client.post('/api/auth/login', data={'username': ids[4], 'password': 'tp'}).json()['access_token']}"}
    return {"th": th, "course_id": cid, "s1": ids[0], "s2": ids[1], "s_other": ids[2]}


def test_roster_enroll_only_class_roster(client: TestClient):
    ctx = _seed_teacher_course(client)
    r = client.post(
        f"/api/subjects/{ctx['course_id']}/roster-enroll",
        headers=ctx["th"],
        json={"student_ids": [ctx["s1"], ctx["s_other"], 999999]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] == 1
    assert body["skipped_not_in_class_roster"] == 1
    assert body["skipped_not_found"] == 1

    r2 = client.post(
        f"/api/subjects/{ctx['course_id']}/roster-enroll",
        headers=ctx["th"],
        json={"student_ids": [ctx["s1"], ctx["s2"]]},
    )
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["skipped_already_enrolled"] == 1
    assert b2["created"] == 1

    db = SessionLocal()
    try:
        n = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.subject_id == ctx["course_id"])
            .count()
        )
        assert n == 2
    finally:
        db.close()


def test_admin_batch_set_class_syncs_student_user(client: TestClient):
    suffix = "adm_bc"
    db = SessionLocal()
    try:
        k1 = Class(name=f"A_{suffix}", grade=1)
        k2 = Class(name=f"B_{suffix}", grade=1)
        db.add_all([k1, k2])
        db.flush()
        st = Student(
            name="调",
            student_no=f"u_{suffix}",
            gender=Gender.MALE,
            class_id=k1.id,
        )
        db.add(st)
        db.flush()
        u = User(
            username=st.student_no,
            hashed_password=get_password_hash("p"),
            real_name="调",
            role=UserRole.STUDENT.value,
            class_id=k1.id,
        )
        db.add(u)
        db.flush()
        uid = u.id
        k2_id = k2.id
        db.commit()
    finally:
        db.close()

    ah = {"Authorization": f"Bearer {client.post('/api/auth/login', data={'username': 'adm', 'password': 'a'}).json()['access_token']}"}
    r = client.post(
        "/api/users/batch-set-class",
        headers=ah,
        json={"user_ids": [uid], "class_id": k2_id},
    )
    assert r.status_code == 200, r.text
    assert r.json()["updated"] == 1
    assert not r.json()["errors"]

    db = SessionLocal()
    try:
        u2 = db.query(User).filter(User.id == uid).first()
        st2 = db.query(Student).filter(Student.student_no == f"u_{suffix}").first()
        assert u2.class_id == k2_id
        assert st2.class_id == k2_id
    finally:
        db.close()


# --- Round 2: API extensions (spec only; implementations deferred) ---


def test_roster_enroll_forbidden_for_student(client: TestClient):
    """Table R1."""
    pytest.skip(_ROUND2)


def test_roster_enroll_forbidden_for_unrelated_teacher(client: TestClient):
    """Table R2."""
    pytest.skip(_ROUND2)


def test_roster_enroll_after_drop_clears_enrollment_block(client: TestClient):
    """Table R3: DELETE student from course then roster-enroll restores enrollment and removes block."""
    pytest.skip(_ROUND2)


def test_roster_enroll_elective_course_sets_enrollment_flags(client: TestClient):
    """Table R4."""
    pytest.skip(_ROUND2)


def test_roster_enroll_rejects_when_course_has_no_class(client: TestClient):
    """Table R5."""
    pytest.skip(_ROUND2)


def test_roster_enroll_empty_student_ids_is_noop(client: TestClient):
    """Table R6."""
    pytest.skip(_ROUND2)


def test_batch_set_class_forbidden_for_non_admin(client: TestClient):
    """Table B1."""
    pytest.skip(_ROUND2)


def test_batch_set_class_mixed_student_and_teacher_ids(client: TestClient):
    """Table B2."""
    pytest.skip(_ROUND2)


def test_batch_set_class_rejects_invalid_class_id(client: TestClient):
    """Table B3."""
    pytest.skip(_ROUND2)


def test_batch_set_class_idempotent_when_already_in_target_class(client: TestClient):
    """Table B4."""
    pytest.skip(_ROUND2)


def test_batch_set_class_aligns_roster_when_mismatched_with_user(client: TestClient):
    """Table B5: User.class_id differs from Student.class_id before batch; both match target after."""
    pytest.skip(_ROUND2)
