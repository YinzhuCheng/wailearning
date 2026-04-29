"""Optional homework placement under course material / chapter."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import CourseMaterial, CourseMaterialChapter, CourseMaterialSection
from tests.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


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


def _ensure_uncategorized_chapter(db, subject_id: int) -> int:
    unc = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == subject_id,
            CourseMaterialChapter.is_uncategorized.is_(True),
        )
        .first()
    )
    if not unc:
        unc = CourseMaterialChapter(
            subject_id=subject_id,
            parent_id=None,
            title="未分类",
            sort_order=0,
            is_uncategorized=True,
        )
        db.add(unc)
        db.commit()
        db.refresh(unc)
    return unc.id


def _uncategorized_chapter_id(db, subject_id: int) -> int:
    return _ensure_uncategorized_chapter(db, subject_id)


def test_homework_linked_to_material_and_chapter_list_filter(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    subject_id = ctx["subject_id"]
    class_id = ctx["class_id"]

    db = SessionLocal()
    try:
        unc = _uncategorized_chapter_id(db, subject_id)
        mat = CourseMaterial(
            title="Unit reading",
            content="body",
            class_id=class_id,
            subject_id=subject_id,
            created_by=ctx["teacher_id"],
        )
        db.add(mat)
        db.flush()
        db.add(CourseMaterialSection(material_id=mat.id, chapter_id=unc, sort_order=0))
        db.commit()
        mid = mat.id
    finally:
        db.close()

    hid = ctx["homework_id"]
    r_put = client.put(
        f"/api/homeworks/{hid}",
        headers=th,
        json={"linked_material_id": mid, "linked_chapter_id": unc},
    )
    assert r_put.status_code == 200, r_put.text
    body = r_put.json()
    assert body["linked_material_id"] == mid
    assert body["linked_chapter_id"] == unc
    assert body.get("linked_material_title") == "Unit reading"

    r_mat = client.get(f"/api/materials/{mid}", headers=th)
    assert r_mat.status_code == 200
    links = r_mat.json().get("linked_homeworks") or []
    assert any(x["id"] == hid for x in links)

    r_ch = client.get(
        "/api/homeworks",
        params={"class_id": class_id, "subject_id": subject_id, "chapter_id": unc},
        headers=th,
    )
    assert r_ch.status_code == 200
    ids = [x["id"] for x in (r_ch.json().get("data") or [])]
    assert hid in ids


def test_homework_material_must_be_placed_in_chapter(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    th = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    subject_id = ctx["subject_id"]
    class_id = ctx["class_id"]

    db = SessionLocal()
    try:
        unc = _uncategorized_chapter_id(db, subject_id)
        ch2 = CourseMaterialChapter(subject_id=subject_id, parent_id=None, title="Other", sort_order=1)
        db.add(ch2)
        db.flush()
        other_ch = ch2.id
        mat = CourseMaterial(
            title="Only in unc",
            content="x",
            class_id=class_id,
            subject_id=subject_id,
            created_by=ctx["teacher_id"],
        )
        db.add(mat)
        db.flush()
        db.add(CourseMaterialSection(material_id=mat.id, chapter_id=unc, sort_order=0))
        db.commit()
        mid = mat.id
    finally:
        db.close()

    hid = ctx["homework_id"]
    bad = client.put(
        f"/api/homeworks/{hid}",
        headers=th,
        json={"linked_material_id": mid, "linked_chapter_id": other_ch},
    )
    assert bad.status_code == 400
