"""Course-scoped homework/material discussion API."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Class, CourseMaterial, Subject, User, UserRole
from tests.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


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


def test_discussion_pagination_counts_replies():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework()
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    hid = ctx["homework_id"]
    sid = ctx["subject_id"]
    cid = ctx["class_id"]

    for i in range(11):
        r = client.post(
            "/api/discussions",
            headers=student_h,
            json={
                "target_type": "homework",
                "target_id": hid,
                "subject_id": sid,
                "class_id": cid,
                "body": f"msg-{i}",
            },
        )
        assert r.status_code == 200, r.text

    p1 = client.get(
        "/api/discussions",
        headers=teacher_h,
        params={
            "target_type": "homework",
            "target_id": hid,
            "subject_id": sid,
            "class_id": cid,
            "page": 1,
            "page_size": 10,
        },
    )
    assert p1.status_code == 200, p1.text
    d1 = p1.json()
    assert d1["total"] == 11
    assert d1["page_size"] == 10
    assert len(d1["data"]) == 10

    p2 = client.get(
        "/api/discussions",
        headers=teacher_h,
        params={
            "target_type": "homework",
            "target_id": hid,
            "subject_id": sid,
            "class_id": cid,
            "page": 2,
            "page_size": 10,
        },
    )
    assert p2.status_code == 200, p2.text
    assert len(p2.json()["data"]) == 1


def test_wrong_class_for_subject_rejected():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework()
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    hid = ctx["homework_id"]
    sid = ctx["subject_id"]

    db = SessionLocal()
    try:
        other = Class(name="other-class", grade=2025)
        db.add(other)
        db.commit()
        db.refresh(other)
        wrong_class_id = other.id
    finally:
        db.close()

    r = client.post(
        "/api/discussions",
        headers=student_h,
        json={
            "target_type": "homework",
            "target_id": hid,
            "subject_id": sid,
            "class_id": wrong_class_id,
            "body": "x",
        },
    )
    assert r.status_code == 400


def test_material_discussion_and_delete():
    _reset_db()
    uid = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        klass = Class(name=f"c-{uid}", grade=2026)
        db.add(klass)
        db.flush()
        t = User(
            username=f"t_{uid}",
            hashed_password=get_password_hash("tp"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(t)
        db.flush()
        course = Subject(name=f"s-{uid}", teacher_id=t.id, class_id=klass.id)
        db.add(course)
        db.flush()
        mat = CourseMaterial(
            title="doc",
            content="c",
            class_id=klass.id,
            subject_id=course.id,
            created_by=t.id,
        )
        db.add(mat)
        db.commit()
        db.refresh(mat)
        mid = mat.id
        sid = course.id
        cid = klass.id
    finally:
        db.close()

    client = TestClient(app)
    th = login_api(client, f"t_{uid}", "tp")
    cr = client.post(
        "/api/discussions",
        headers=th,
        json={
            "target_type": "material",
            "target_id": mid,
            "subject_id": sid,
            "class_id": cid,
            "body": "note",
        },
    )
    assert cr.status_code == 200, cr.text
    eid = cr.json()["id"]

    dl = client.delete(f"/api/discussions/{eid}", headers=th)
    assert dl.status_code == 204

    lst = client.get(
        "/api/discussions",
        headers=th,
        params={
            "target_type": "material",
            "target_id": mid,
            "subject_id": sid,
            "class_id": cid,
        },
    )
    assert lst.status_code == 200
    assert lst.json()["total"] == 0
