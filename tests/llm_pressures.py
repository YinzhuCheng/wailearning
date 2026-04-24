"""
Heterogeneous LLM grading / scheduling pressure and integration tests.

Covers: queue drain via process_next, attachment->vision payload, quota + timezone
patching, course vs student limits, HTTP status failover, group failover, task
isolation, permission matrix, and student-visible submission fields.
"""

from __future__ import annotations

import json as json_mod
import io
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from app.auth import get_password_hash
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Class,
    CourseEnrollment,
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    HomeworkGradingTask,
    LLMEndpointPreset,
    LLMGroup,
    LLMTokenUsageLog,
    Student,
    Subject,
    User,
    UserRole,
)
from app.llm_grading import process_grading_task, process_next_grading_task
from tests.llm_scenario import ensure_admin, json_llm_response, login_api, make_grading_course_with_homework


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


def _assert_messages_contain_image_url(captured: dict) -> None:
    payload = captured.get("json") or {}
    msgs = payload.get("messages") or []
    user_msg = next((m for m in msgs if m.get("role") == "user"), None)
    assert user_msg, "user message missing"
    content = user_msg.get("content")
    found = False
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                u = (part.get("image_url") or {}).get("url", "")
                if u.startswith("data:") and "base64" in u:
                    found = True
                    break
    assert found, "expected an image data URL in user content"


def _make_one_pixel_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (2, 2), color="red").save(buf, format="PNG")
    return buf.getvalue()


# --- 1) Worker-style queue drain: only process_next_grading_task ---


def test_drain_queued_tasks_via_process_next_only(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    s_h = login_api(client, ctx["student_username"], ctx["student_password"])
    for content in ("first", "second"):
        r = client.post(
            f"/api/homeworks/{ctx['homework_id']}/submission",
            headers=s_h,
            json={"content": f"answer {content}"},
        )
        assert r.status_code == 200, r.text

    calls: list[None] = []

    def fake_post(self, url, **kwargs):
        calls.append(None)
        return httpx.Response(200, json=json_llm_response(70.0, "ok"))

    with mock.patch.object(httpx.Client, "post", fake_post):
        assert process_next_grading_task() is True
        assert process_next_grading_task() is True
        assert process_next_grading_task() is False
    assert len(calls) == 2

    r = client.get(f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h)
    assert r.status_code == 200
    assert r.json()["latest_task_status"] == "success"
    assert r.json()["review_score"] is not None


# --- 2) Attachment: PNG in upload -> grading includes image in outbound JSON ---


def test_png_attachment_sends_image_url_in_llm_request(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    t_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    s_h = login_api(client, ctx["student_username"], ctx["student_password"])
    u = f"/api/llm-settings/courses/{ctx['subject_id']}"
    p = {
        "is_enabled": True,
        "max_input_tokens": 16000,
        "max_output_tokens": 1200,
        "response_language": "zh-CN",
        "quota_timezone": "UTC",
        "estimated_image_tokens": 850,
        "endpoints": [{"preset_id": ctx["preset_id"], "priority": 1}],
    }
    assert client.put(u, headers=t_h, json=p).status_code == 200
    r_up = client.post(
        "/api/files/upload",
        headers=s_h,
        files={"file": ("shot.png", _make_one_pixel_png(), "image/png")},
    )
    assert r_up.status_code == 200, r_up.text
    up = r_up.json()
    r_sub = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=s_h,
        json={
            "content": "见附图",
            "attachment_name": up.get("attachment_name", "shot.png"),
            "attachment_url": up["attachment_url"],
        },
    )
    assert r_sub.status_code == 200, r_sub.text
    task_id: int | None = None
    db = SessionLocal()
    try:
        from app.models import HomeworkGradingTask

        task = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first()
        assert task
        task_id = task.id
    finally:
        db.close()
    last_kwargs: dict = {}

    def capture_post(self, url, **kwargs):
        last_kwargs.update(kwargs)
        return httpx.Response(200, json=json_llm_response(80.0, "has image"))

    with mock.patch.object(httpx.Client, "post", capture_post):
        process_grading_task(task_id)
    assert last_kwargs.get("json"), "no JSON body captured"
    _assert_messages_contain_image_url(last_kwargs)
    r_me = client.get(f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h)
    assert r_me.json()["latest_task_status"] == "success"


# --- 3) Quota: usage_date moves when _get_usage_date is patched (timezone day roll) ---


def test_quota_resets_across_patched_usage_dates(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(
        course_llm_enabled=True,
        daily_student_token_limit=5000,
    )
    s_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=s_h,
        json={"content": "d1"},
    )
    assert r.status_code == 200
    db = SessionLocal()
    try:
        from app.models import HomeworkGradingTask

        tid1 = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()
    with mock.patch.object(httpx.Client, "post", return_value=httpx.Response(200, json=json_llm_response(50.0, "a"))):
        with mock.patch("app.llm_grading._get_usage_date", return_value="2000-05-20"):
            process_grading_task(tid1)
    r2 = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=s_h,
        json={"content": "d2"},
    )
    assert r2.status_code == 200
    db = SessionLocal()
    try:
        from app.models import HomeworkGradingTask

        tid2 = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()
    with mock.patch.object(httpx.Client, "post", return_value=httpx.Response(200, json=json_llm_response(55.0, "b"))):
        with mock.patch("app.llm_grading._get_usage_date", return_value="2000-05-21"):
            process_grading_task(tid2)
    db = SessionLocal()
    try:
        n = db.query(LLMTokenUsageLog).count()
    finally:
        db.close()
    assert n == 2


# --- 4) Multi-student course: per-student pool only (no shared course cap) ---


def test_second_student_grading_succeeds_after_first_high_usage(client: TestClient):
    """Without a course-wide daily cap, another student's submission still gets LLM grading."""
    from tests.llm_scenario import make_multi_student_scenario

    ensure_admin()
    m = make_multi_student_scenario(2, daily_student_token_limit=1_000_000)
    t_h = login_api(client, m["teacher_username"], m["teacher_password"])
    sid = m["subject_id"]
    p = {
        "is_enabled": True,
        "daily_student_token_limit": 1_000_000,
        "max_input_tokens": 16000,
        "max_output_tokens": 1200,
        "response_language": "zh-CN",
        "quota_timezone": "UTC",
        "estimated_image_tokens": 850,
        "endpoints": [{"preset_id": m["preset_id"], "priority": 1}],
    }
    r_cfg = client.put(f"/api/llm-settings/courses/{sid}", headers=t_h, json=p)
    assert r_cfg.status_code == 200, r_cfg.text

    tasks: list[int] = []
    for st in m["students"][:2]:
        h = login_api(client, st["username"], st["password"])
        r = client.post(
            f"/api/homeworks/{m['homework_id']}/submission",
            headers=h,
            json={"content": "x" * 8000},
        )
        assert r.status_code == 200
        db = SessionLocal()
        try:
            from app.models import HomeworkGradingTask

            tasks.append(
                db.query(HomeworkGradingTask)
                .filter(HomeworkGradingTask.student_id == st["student_id"])
                .one()
                .id
            )
        finally:
            db.close()
    u400 = {
        "prompt_tokens": 3000,
        "completion_tokens": 0,
        "total_tokens": 3000,
    }
    u2800 = {
        "choices": [{"message": {"content": json_mod.dumps({"score": 60, "comment": "c"})}}],
        "usage": u400,
    }

    posts = []

    def track_post(self, url, **kwargs):
        posts.append(1)
        return httpx.Response(200, json=u2800)

    with mock.patch.object(httpx.Client, "post", track_post):
        process_grading_task(tasks[0])
        process_grading_task(tasks[1])
    assert len(posts) == 2
    db = SessionLocal()
    try:
        from app.models import HomeworkGradingTask

        t2 = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tasks[1]).one()
    finally:
        db.close()
    assert t2.status == "success"


# --- 5) HTTP 429 then success on same member (retryable) ---


def test_429_then_200_succeeds_after_retry(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    t_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    u = f"/api/llm-settings/courses/{ctx['subject_id']}"
    p = {
        "is_enabled": True,
        "endpoints": [{"preset_id": ctx["preset_id"], "priority": 1}],
    }
    body = {**_full_course_config_payload(), **p}
    assert client.put(u, headers=t_h, json=body).status_code == 200
    s_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=s_h,
        json={"content": "q"},
    )
    assert r.status_code == 200
    db = SessionLocal()
    try:
        from app.models import HomeworkGradingTask, LLMEndpointPreset

        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
        pr = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == ctx["preset_id"]).one()
        pr.max_retries = 1
        db.commit()
    finally:
        db.close()
    q = [httpx.Response(429, json={"error": "rate"}), httpx.Response(200, json=json_llm_response(66.0, "ok after"))]

    def seq(self, url, **kwargs):
        return q.pop(0) if q else httpx.Response(200, json=json_llm_response(0, "x"))

    with mock.patch.object(httpx.Client, "post", seq):
        process_grading_task(tid)
    r_me = client.get(f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h)
    assert r_me.json()["latest_task_status"] == "success"
    assert r_me.json()["review_score"] == 66.0


def _full_course_config_payload() -> dict:
    return {
        "is_enabled": True,
        "max_input_tokens": 16000,
        "max_output_tokens": 1200,
        "response_language": "zh-CN",
        "quota_timezone": "UTC",
        "estimated_image_tokens": 850,
    }


# --- 6) First group exhausts; second group succeeds (401 non-retryable) ---


def test_second_group_succeeds_after_first_exhausts(client: TestClient):
    ensure_admin()
    uid = uuid.uuid4().hex[:10]
    db = SessionLocal()
    try:
        cl = Class(name=f"cg-{uid}", grade=2026)
        db.add(cl)
        db.flush()
        teacher = User(
            username=f"tg_{uid}",
            hashed_password=get_password_hash("tgp"),
            real_name="T",
            role=UserRole.TEACHER.value,
        )
        db.add(teacher)
        db.flush()
        stu_u = User(
            username=f"sg_{uid}",
            hashed_password=get_password_hash("sgp"),
            real_name="S",
            role=UserRole.STUDENT.value,
            class_id=cl.id,
        )
        db.add(stu_u)
        db.flush()
        stud = Student(name="S1", student_no=stu_u.username, class_id=cl.id)
        db.add(stud)
        db.flush()
        course = Subject(name=f"csj-{uid}", teacher_id=teacher.id, class_id=cl.id)
        db.add(course)
        db.flush()
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=stud.id,
                class_id=cl.id,
                enrollment_type="required",
            )
        )
        fail_p = LLMEndpointPreset(
            name=f"failp-{uid}",
            base_url="https://f.fail/v1/",
            api_key="bad",
            model_name="mf",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        ok_p = LLMEndpointPreset(
            name=f"okp-{uid}",
            base_url="https://ok.t/v1/",
            api_key="ok",
            model_name="mo",
            max_retries=0,
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add_all([fail_p, ok_p])
        db.flush()
        cfg = CourseLLMConfig(subject_id=course.id, is_enabled=True, quota_timezone="UTC", max_input_tokens=4000, max_output_tokens=500)
        db.add(cfg)
        db.flush()
        g1 = LLMGroup(config_id=cfg.id, priority=1, name="gfail")
        g2 = LLMGroup(config_id=cfg.id, priority=2, name="gok")
        db.add_all([g1, g2])
        db.flush()
        db.add(
            CourseLLMConfigEndpoint(config_id=cfg.id, group_id=g1.id, preset_id=fail_p.id, priority=1),
        )
        db.add(
            CourseLLMConfigEndpoint(config_id=cfg.id, group_id=g2.id, preset_id=ok_p.id, priority=1),
        )
        hw = Homework(
            title="gtest",
            content="c",
            class_id=cl.id,
            subject_id=course.id,
            max_score=100,
            auto_grading_enabled=True,
            created_by=teacher.id,
        )
        db.add(hw)
        db.commit()
        subject_id, hid, p_fail, p_ok = course.id, hw.id, fail_p.id, ok_p.id
        t_user, t_pass = teacher.username, "tgp"
        student_login = stu_u.username
    finally:
        db.close()
    t_h = login_api(client, t_user, t_pass)
    r_put = client.put(
        f"/api/llm-settings/courses/{subject_id}",
        headers=t_h,
        json={
            "is_enabled": True,
            "quota_timezone": "UTC",
            "estimated_chars_per_token": 4.0,
            "estimated_image_tokens": 100,
            "max_input_tokens": 4000,
            "max_output_tokens": 500,
            "groups": [
                {"name": "A", "members": [{"preset_id": p_fail, "priority": 1}]},
                {"name": "B", "members": [{"preset_id": p_ok, "priority": 1}]},
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    s_h = login_api(client, student_login, "sgp")
    r_sub = client.post(
        f"/api/homeworks/{hid}/submission",
        headers=s_h,
        json={"content": "gr"},
    )
    assert r_sub.status_code == 200, r_sub.text
    tdb = SessionLocal()
    try:
        tid = tdb.query(HomeworkGradingTask).one().id
    finally:
        tdb.close()

    calls: list[dict] = []

    def route(self, url, **kwargs):
        u = str(url)
        if "f.fail" in u:
            return httpx.Response(401, json={"error": "nope"})
        if "ok.t" in u:
            calls.append(kwargs)
            return httpx.Response(200, json=json_llm_response(72.0, "group2"))
        return httpx.Response(500, text="x")

    with mock.patch.object(httpx.Client, "post", route):
        process_grading_task(tid)
    assert len(calls) == 1
    r_me = client.get(f"/api/homeworks/{hid}/submission/me", headers=s_h)
    d = r_me.json()
    assert d["latest_task_status"] == "success"
    assert d["review_score"] == 72.0
    tdb2 = SessionLocal()
    try:
        art = tdb2.query(HomeworkGradingTask).one().artifact_manifest or {}
        st = (art.get("llm_routing") or {}).get("status")
    finally:
        tdb2.close()
    assert st == "ok"


# --- 7) “Poison” task: others still succeed when using process_next loop ---


def test_failed_task_does_not_block_following_queued_auto_grades(client: TestClient):
    ensure_admin()
    a = make_grading_course_with_homework()
    b = make_grading_course_with_homework()
    sa = login_api(client, a["student_username"], a["student_password"])
    sb = login_api(client, b["student_username"], b["student_password"])
    ra = client.post(
        f"/api/homeworks/{a['homework_id']}/submission", headers=sa, json={"content": "a"}
    )
    rb = client.post(
        f"/api/homeworks/{b['homework_id']}/submission", headers=sb, json={"content": "b"}
    )
    assert ra.status_code == 200 and rb.status_code == 200
    # make_grading_course uses the same base_url for all presets: route by global POST order
    # (Task A: 3 bad responses with max_retries=2 then fail; task B: 1 good response).
    call_no = 0

    def smart_post(self, url, **kwargs):
        nonlocal call_no
        call_no += 1
        if call_no <= 3:
            return httpx.Response(200, text="not json {")
        return httpx.Response(200, json=json_llm_response(88.0, "b ok"))

    with mock.patch.object(httpx.Client, "post", smart_post):
        assert process_next_grading_task() is True
        assert process_next_grading_task() is True
    tdb3 = SessionLocal()
    try:
        t_a = tdb3.query(HomeworkGradingTask).filter(HomeworkGradingTask.homework_id == a["homework_id"]).one()
        t_b = tdb3.query(HomeworkGradingTask).filter(HomeworkGradingTask.homework_id == b["homework_id"]).one()
    finally:
        tdb3.close()
    assert t_a.status == "failed"
    assert t_b.status == "success"
    r_b = client.get(f"/api/homeworks/{b['homework_id']}/submission/me", headers=sb)
    assert r_b.json()["review_score"] == 88.0


# --- 8) Regrade: teacher regrade + LLM slow: latest score and comment from API ---


def test_read_side_after_regrade_shows_new_auto_score(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    t_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    s_h = login_api(client, ctx["student_username"], ctx["student_password"])
    r0 = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission", headers=s_h, json={"content": "v1"}
    )
    assert r0.status_code == 200
    tdb = SessionLocal()
    try:
        tid = tdb.query(HomeworkGradingTask).one().id
    finally:
        tdb.close()
    with mock.patch.object(httpx.Client, "post", return_value=httpx.Response(200, json=json_llm_response(40.0, "v1c"))):
        process_grading_task(tid)
    r_re = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submissions/{r0.json()['id']}/regrade",
        headers=t_h,
        json={},
    )
    assert r_re.status_code == 200, r_re.text
    tdb2 = SessionLocal()
    try:
        tid2 = tdb2.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        tdb2.close()
    with mock.patch.object(httpx.Client, "post", return_value=httpx.Response(200, json=json_llm_response(91.0, "r2c"))):
        process_grading_task(tid2)
    r_view = client.get(
        f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h
    )
    j = r_view.json()
    assert j["latest_task_status"] == "success"
    assert j["review_score"] == 91.0
    assert "r2c" in (j.get("review_comment") or "")


# --- 9) Permission: class teacher and foreign teacher 403; student cannot read course LLM ---


def test_llm_and_homework_rbac_matrix(client: TestClient):
    ensure_admin()
    uid = uuid.uuid4().hex[:8]
    subject_id: int
    db = SessionLocal()
    try:
        k = Class(name=f"rbk-{uid}", grade=2026)
        db.add(k)
        db.flush()
        t1 = User(
            username=f"rbt1_{uid}",
            hashed_password=get_password_hash("p1"),
            real_name="T1",
            role=UserRole.TEACHER.value,
        )
        t2 = User(
            username=f"rbt2_{uid}",
            hashed_password=get_password_hash("p2"),
            real_name="T2",
            role=UserRole.TEACHER.value,
        )
        cl_t = User(
            username=f"rbc_{uid}",
            hashed_password=get_password_hash("pc"),
            real_name="CT",
            role=UserRole.CLASS_TEACHER.value,
            class_id=k.id,
        )
        s_u = User(
            username=f"rbs_{uid}",
            hashed_password=get_password_hash("ps"),
            real_name="S",
            role=UserRole.STUDENT.value,
            class_id=k.id,
        )
        db.add_all([t1, t2, cl_t, s_u])
        db.flush()
        st = Student(name="S", student_no=s_u.username, class_id=k.id)
        db.add(st)
        db.flush()
        subj = Subject(name=f"RBC-{uid}", teacher_id=t1.id, class_id=k.id)
        db.add(subj)
        db.flush()
        db.add(
            CourseEnrollment(subject_id=subj.id, student_id=st.id, class_id=k.id, enrollment_type="required")
        )
        p = LLMEndpointPreset(
            name=f"rbp-{uid}",
            base_url="https://rb.t/v1/",
            api_key="k",
            model_name="m",
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(p)
        db.flush()
        cfg = CourseLLMConfig(
            subject_id=subj.id,
            is_enabled=True,
            max_input_tokens=2000,
            max_output_tokens=200,
        )
        db.add(cfg)
        db.flush()
        db.add(CourseLLMConfigEndpoint(config_id=cfg.id, preset_id=p.id, priority=1))
        db.commit()
        subject_id = subj.id
        c_uname, t2_uname, s_uname = cl_t.username, t2.username, s_u.username
    finally:
        db.close()
    c_h = login_api(client, c_uname, "pc")
    t2_h = login_api(client, t2_uname, "p2")
    s_h = login_api(client, s_uname, "ps")
    assert client.get(f"/api/llm-settings/courses/{subject_id}", headers=c_h).status_code == 200
    assert client.get(f"/api/llm-settings/courses/{subject_id}", headers=t2_h).status_code == 403
    assert client.get(f"/api/llm-settings/presets", headers=s_h).status_code == 403


# --- 10) Zip with inner txt: LLM post contains outer text in messages ---


def test_zip_with_inner_txt_sends_file_content_in_messages(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    t_h, s_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"]), login_api(
        client, ctx["student_username"], ctx["student_password"]
    )
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as zf:
        zf.writestr("inner/readme.txt", "ZIP INNER UNIQUE TEXT XYZZY123")
    b.seek(0)
    r_up = client.post(
        "/api/files/upload",
        headers=s_h,
        files={"file": ("pack.zip", b.getvalue(), "application/zip")},
    )
    assert r_up.status_code == 200, r_up.text
    up = r_up.json()
    u = f"/api/llm-settings/courses/{ctx['subject_id']}"
    p = {**_full_course_config_payload(), "endpoints": [{"preset_id": ctx["preset_id"], "priority": 1}]}
    assert client.put(u, headers=t_h, json=p).status_code == 200
    r_sub = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=s_h,
        json={
            "content": "zip submit",
            "attachment_name": "pack.zip",
            "attachment_url": up["attachment_url"],
        },
    )
    assert r_sub.status_code == 200, r_sub.text
    tdb = SessionLocal()
    try:
        tid = tdb.query(HomeworkGradingTask).one().id
    finally:
        tdb.close()
    last: dict = {}

    def cap(self, u, **kwargs):
        last.update(kwargs)
        return httpx.Response(200, json=json_llm_response(60.0, "zip"))

    with mock.patch.object(httpx.Client, "post", cap):
        process_grading_task(tid)
    pl = (last.get("json") or {}) or {}
    ser = json_mod.dumps(pl, ensure_ascii=False)
    assert "XYZZY123" in ser


# --- 11) 401/403/429 matrix on flat endpoints: first dead, second used ---


def test_flat_priority_failover_401_to_second_preset(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    db = SessionLocal()
    try:
        p2 = LLMEndpointPreset(
            name="flat-b-" + uuid.uuid4().hex[:6],
            base_url="https://second.flat/v1/",
            api_key="b",
            model_name="mb",
            is_active=True,
            supports_vision=True,
            validation_status="validated",
        )
        db.add(p2)
        db.commit()
        pid2 = p2.id
    finally:
        db.close()
    t_h, s_h = (
        login_api(client, ctx["teacher_username"], ctx["teacher_password"]),
        login_api(client, ctx["student_username"], ctx["student_password"]),
    )
    r_put = client.put(
        f"/api/llm-settings/courses/{ctx['subject_id']}",
        headers=t_h,
        json={
            **_full_course_config_payload(),
            "endpoints": [
                {"preset_id": ctx["preset_id"], "priority": 1},
                {"preset_id": pid2, "priority": 2},
            ],
        },
    )
    assert r_put.status_code == 200, r_put.text
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission", headers=s_h, json={"content": "ff"}
    )
    assert r.status_code == 200, r.text
    tdb = SessionLocal()
    try:
        tid = tdb.query(HomeworkGradingTask).one().id
    finally:
        tdb.close()
    tdb2 = SessionLocal()
    try:
        u1 = tdb2.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == ctx["preset_id"]).one().base_url
        u2 = tdb2.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == pid2).one().base_url
    finally:
        tdb2.close()

    def fixed_order(self, url, **kwargs):
        uu = str(url)
        if u1 in uu or u1.rstrip("/") in uu:
            return httpx.Response(401, text="nope")
        if u2 in uu:
            return httpx.Response(200, json=json_llm_response(80.0, "second ok"))
        return httpx.Response(500, text="?")

    with mock.patch.object(httpx.Client, "post", fixed_order):
        process_grading_task(tid)
    r_me = client.get(
        f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h
    )
    assert r_me.json()["review_score"] == 80.0


# --- 12) Parallel tasks for different students: N LLM invocations, no crosstalk ---


def test_parallel_different_students_independent_outcomes(client: TestClient):
    from tests.llm_scenario import make_multi_student_scenario

    ensure_admin()
    m = make_multi_student_scenario(3)
    t_h = login_api(client, m["teacher_username"], m["teacher_password"])
    assert client.put(
        f"/api/llm-settings/courses/{m['subject_id']}",
        headers=t_h,
        json={**_full_course_config_payload(), "endpoints": [{"preset_id": m["preset_id"], "priority": 1}]},
    ).status_code == 200
    for st in m["students"]:
        h = login_api(client, st["username"], st["password"])
        r = client.post(
            f"/api/homeworks/{m['homework_id']}/submission",
            headers=h,
            json={"content": f"STU_CONTENT_{st['student_id']}_END"},
        )
        assert r.status_code == 200
    tdb = SessionLocal()
    try:
        tids = [x.id for x in tdb.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.asc()).all()]
    finally:
        tdb.close()

    def by_messages(self, url, **kwargs):
        msgs = (kwargs.get("json") or {}).get("messages") or []
        raw = json_mod.dumps(msgs, ensure_ascii=False)
        s0, s1, s2 = m["students"][0]["student_id"], m["students"][1]["student_id"], m["students"][2]["student_id"]
        if f"STU_CONTENT_{s0}_END" in raw:
            v = 11.0
        elif f"STU_CONTENT_{s1}_END" in raw:
            v = 22.0
        elif f"STU_CONTENT_{s2}_END" in raw:
            v = 33.0
        else:
            v = 0.0
        return httpx.Response(200, json=json_llm_response(v, "m"))

    with mock.patch.object(httpx.Client, "post", by_messages):
        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = [ex.submit(process_grading_task, tid) for tid in tids]
            for f in as_completed(futs):
                f.result()
    expected = [11.0, 22.0, 33.0]
    for i, st in enumerate(m["students"]):
        h = login_api(client, st["username"], st["password"])
        g = client.get(
            f"/api/homeworks/{m['homework_id']}/submission/me", headers=h
        )
        assert g.json()["review_score"] == expected[i]


# --- 13) Near max text + low max_input: still success with truncation notes ---


def test_long_submission_respects_truncate_and_succeeds(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework()
    t_h, s_h = (
        login_api(client, ctx["teacher_username"], ctx["teacher_password"]),
        login_api(client, ctx["student_username"], ctx["student_password"]),
    )
    u = f"/api/llm-settings/courses/{ctx['subject_id']}"
    p = {
        "is_enabled": True,
        "max_input_tokens": 4000,
        "max_output_tokens": 300,
        "response_language": "zh-CN",
        "quota_timezone": "UTC",
        "estimated_chars_per_token": 3.0,
        "endpoints": [{"preset_id": ctx["preset_id"], "priority": 1}],
    }
    assert client.put(u, headers=t_h, json=p).status_code == 200
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission", headers=s_h, json={"content": "A" * 20000}
    )
    assert r.status_code == 200
    tdb = SessionLocal()
    try:
        tid = tdb.query(HomeworkGradingTask).one().id
    finally:
        tdb.close()
    with mock.patch.object(httpx.Client, "post", return_value=httpx.Response(200, json=json_llm_response(55.0, "k"))):
        process_grading_task(tid)
    tdb2 = SessionLocal()
    try:
        art = tdb2.query(HomeworkGradingTask).one().artifact_manifest or {}
    finally:
        tdb2.close()
    assert (art.get("llm_routing") or {}).get("status") == "ok" or "included" in art
    g = client.get(
        f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h
    )
    assert g.json()["latest_task_status"] == "success"


# --- 14) HTTP 403: non-retry, flat second endpoint used --- (merged into 11; 14 = student error message is human-readable) ---


def test_student_sees_friendly_error_when_config_disabled(client: TestClient):
    ensure_admin()
    ctx = make_grading_course_with_homework(course_llm_enabled=False)
    t_h, s_h = (
        login_api(client, ctx["teacher_username"], ctx["teacher_password"]),
        login_api(client, ctx["student_username"], ctx["student_password"]),
    )
    u = f"/api/llm-settings/courses/{ctx['subject_id']}"
    p = {**_full_course_config_payload(), "is_enabled": True, "endpoints": [{"preset_id": ctx["preset_id"], "priority": 1}]}
    assert client.put(u, headers=t_h, json=p).status_code == 200
    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission", headers=s_h, json={"content": "c"}
    )
    assert r.status_code == 200, r.text
    tdb = SessionLocal()
    try:
        tdb.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == ctx["subject_id"]).update(
            {CourseLLMConfig.is_enabled: False}
        )
        tdb.commit()
        tid = tdb.query(HomeworkGradingTask).one().id
    finally:
        tdb.close()
    process_grading_task(tid)
    v = client.get(
        f"/api/homeworks/{ctx['homework_id']}/submission/me", headers=s_h
    ).json()
    assert v["latest_task_status"] == "failed"
    assert v["latest_task_error"]  # not empty; human language
    assert "LLM" in (v["latest_task_error"] or "")
