"""Roster-only course enrollment and admin batch class assignment."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, CourseEnrollment, Gender, Student, Subject, User, UserRole


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
