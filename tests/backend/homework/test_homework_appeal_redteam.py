"""Red-team checks for homework appeal state transitions and gating."""

from __future__ import annotations

from fastapi.testclient import TestClient

from apps.backend.courseeval_backend.main import app
from apps.backend.courseeval_backend.db.database import SessionLocal
from tests.scenarios.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


def _reset_db() -> None:
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.courseeval_backend.bootstrap import ensure_schema_updates

    ensure_schema_updates()


def test_student_cannot_appeal_when_auto_grading_failed_without_score_or_comment():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework()
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    hid = ctx["homework_id"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "failed appeal gate"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    from apps.backend.courseeval_backend.llm_grading import process_grading_task
    from apps.backend.courseeval_backend.db.models import HomeworkGradingTask
    from unittest import mock
    import httpx

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(500, text="llm failed hard without payload"),
    ):
        process_grading_task(tid)

    appeal = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/appeal",
        headers=student_h,
        json={"reason_text": "this should stay blocked after grading failed"},
    )
    assert appeal.status_code == 400, appeal.text


def test_acknowledge_appeal_marks_notifications_as_acknowledged_not_resolved():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    hid = ctx["homework_id"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "ack title guard"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    review = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 91, "review_comment": "pre-appeal score"},
    )
    assert review.status_code == 200, review.text

    appeal = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/appeal",
        headers=student_h,
        json={"reason_text": "please recheck this scoring decision carefully"},
    )
    assert appeal.status_code == 200, appeal.text

    noted = client.get("/api/notifications", headers=teacher_h)
    assert noted.status_code == 200, noted.text
    before = [row for row in noted.json().get("data", []) if row.get("notification_kind") == "grade_appeal"]
    assert before
    assert any("已处理" not in str(row.get("title") or "") for row in before)

    ack = client.post(f"/api/homeworks/{hid}/submissions/{sub_id}/appeal/acknowledge", headers=teacher_h)
    assert ack.status_code == 200, ack.text
    assert ack.json()["status"] == "acknowledged"

    after_resp = client.get("/api/notifications", headers=teacher_h)
    assert after_resp.status_code == 200, after_resp.text
    after = [row for row in after_resp.json().get("data", []) if row.get("notification_kind") == "grade_appeal"]
    assert after
    assert any("已阅" in str(row.get("title") or "") for row in after)
    assert all("已处理" not in str(row.get("title") or "") for row in after)


def test_review_after_acknowledge_moves_appeal_to_resolved_state():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    hid = ctx["homework_id"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "ack then resolve"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    review = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 70, "review_comment": "initial score before appeal"},
    )
    assert review.status_code == 200, review.text

    appeal = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/appeal",
        headers=student_h,
        json={"reason_text": "please check this scoring decision one more time"},
    )
    assert appeal.status_code == 200, appeal.text

    ack = client.post(f"/api/homeworks/{hid}/submissions/{sub_id}/appeal/acknowledge", headers=teacher_h)
    assert ack.status_code == 200, ack.text
    assert ack.json()["status"] == "acknowledged"

    resolved = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 85, "review_comment": "resolved after teacher review"},
    )
    assert resolved.status_code == 200, resolved.text

    from apps.backend.courseeval_backend.db.models import HomeworkGradeAppeal

    db = SessionLocal()
    try:
        row = db.query(HomeworkGradeAppeal).filter(HomeworkGradeAppeal.submission_id == sub_id).first()
        assert row is not None
        assert row.status == "resolved"
    finally:
        db.close()

    after_resp = client.get("/api/notifications", headers=teacher_h)
    assert after_resp.status_code == 200, after_resp.text
    after = [row for row in after_resp.json().get("data", []) if row.get("notification_kind") == "grade_appeal"]
    assert after
    assert any("已处理" in str(row.get("title") or "") for row in after)


def test_llm_regrade_resolves_pending_homework_appeal_after_success():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=True, course_llm_enabled=True)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    hid = ctx["homework_id"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "appeal then regrade"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    from apps.backend.courseeval_backend.llm_grading import process_grading_task
    from apps.backend.courseeval_backend.db.models import HomeworkGradingTask, HomeworkGradeAppeal, HomeworkSubmission
    from tests.scenarios.llm_scenario import json_llm_response
    from unittest import mock
    import httpx

    db = SessionLocal()
    try:
        first_tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(61.0, "first auto score")),
    ):
        process_grading_task(first_tid)

    appeal = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/appeal",
        headers=student_h,
        json={"reason_text": "please re-run grading because the first result missed points"},
    )
    assert appeal.status_code == 200, appeal.text

    regrade = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/regrade",
        headers=teacher_h,
        json={},
    )
    assert regrade.status_code == 200, regrade.text

    db = SessionLocal()
    try:
        second_tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(88.0, "regrade fixed result")),
    ):
        process_grading_task(second_tid)

    db = SessionLocal()
    try:
        row = db.query(HomeworkGradeAppeal).filter(HomeworkGradeAppeal.submission_id == sub_id).first()
        assert row is not None
        summary = db.query(HomeworkSubmission).filter(HomeworkSubmission.id == sub_id).first()
        assert summary is not None
        assert summary.latest_task_status == "success"
        assert summary.review_score is not None
        assert row.status == "resolved"
    finally:
        db.close()

    after_resp = client.get("/api/notifications", headers=teacher_h)
    assert after_resp.status_code == 200, after_resp.text
    after = [row for row in after_resp.json().get("data", []) if row.get("notification_kind") == "grade_appeal"]
    assert after
    assert any("已处理" in str(row.get("title") or "") for row in after)


def test_notification_detail_after_resolved_appeal_uses_resolved_title_not_acknowledged_title():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    hid = ctx["homework_id"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "detail title drift"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    review = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 73, "review_comment": "before appeal"},
    )
    assert review.status_code == 200, review.text

    appeal = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/appeal",
        headers=student_h,
        json={"reason_text": "please check the scoring details again"},
    )
    assert appeal.status_code == 200, appeal.text

    ack = client.post(f"/api/homeworks/{hid}/submissions/{sub_id}/appeal/acknowledge", headers=teacher_h)
    assert ack.status_code == 200, ack.text

    resolved = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 86, "review_comment": "after resolution"},
    )
    assert resolved.status_code == 200, resolved.text

    listed = client.get("/api/notifications", headers=teacher_h)
    assert listed.status_code == 200, listed.text
    grade_rows = [row for row in listed.json().get("data", []) if row.get("notification_kind") == "grade_appeal"]
    assert grade_rows
    notif_id = grade_rows[0]["id"]

    detail = client.get(f"/api/notifications/{notif_id}", headers=teacher_h)
    assert detail.status_code == 200, detail.text
    title = str(detail.json().get("title") or "")
    assert "已处理" in title
    assert "已阅" not in title


def test_resolved_grade_appeal_notification_exposes_appeal_status_to_clients():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])
    hid = ctx["homework_id"]

    sub = client.post(f"/api/homeworks/{hid}/submission", headers=student_h, json={"content": "status field gap"})
    assert sub.status_code == 200, sub.text
    sub_id = sub.json()["id"]

    review = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 71, "review_comment": "before appeal"},
    )
    assert review.status_code == 200, review.text

    appeal = client.post(
        f"/api/homeworks/{hid}/submissions/{sub_id}/appeal",
        headers=student_h,
        json={"reason_text": "please check this score and comment once more"},
    )
    assert appeal.status_code == 200, appeal.text

    resolved = client.put(
        f"/api/homeworks/{hid}/submissions/{sub_id}/review",
        headers=teacher_h,
        json={"review_score": 89, "review_comment": "resolved after teacher review"},
    )
    assert resolved.status_code == 200, resolved.text

    listed = client.get("/api/notifications", headers=teacher_h)
    assert listed.status_code == 200, listed.text
    grade_rows = [row for row in listed.json().get("data", []) if row.get("notification_kind") == "grade_appeal"]
    assert grade_rows
    assert any(row.get("appeal_status") == "resolved" for row in grade_rows)


def test_resolved_score_appeal_notification_exposes_appeal_status_to_clients():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    created = client.post(
        f"/api/scores/appeals?subject_id={ctx['subject_id']}",
        headers=student_h,
        json={"semester": "2026-fall", "target_component": "total", "reason_text": "score appeal status field"},
    )
    assert created.status_code == 200, created.text
    appeal_id = created.json()["id"]

    resolved = client.put(
        f"/api/scores/appeals/{appeal_id}",
        headers=teacher_h,
        json={"teacher_response": "resolved", "status": "resolved"},
    )
    assert resolved.status_code == 200, resolved.text

    listed = client.get("/api/notifications", headers=teacher_h)
    assert listed.status_code == 200, listed.text
    rows = [row for row in listed.json().get("data", []) if row.get("notification_kind") == "score_grade_appeal"]
    assert rows
    assert any(row.get("appeal_status") == "resolved" for row in rows)


def test_pending_score_appeal_notification_exposes_appeal_status_to_clients():
    _reset_db()
    ensure_admin()
    ctx = make_grading_course_with_homework(auto_grading=False, course_llm_enabled=False)
    client = TestClient(app)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    teacher_h = login_api(client, ctx["teacher_username"], ctx["teacher_password"])

    created = client.post(
        f"/api/scores/appeals?subject_id={ctx['subject_id']}",
        headers=student_h,
        json={"semester": "2026-fall", "target_component": "total", "reason_text": "score appeal pending state"},
    )
    assert created.status_code == 200, created.text

    listed = client.get("/api/notifications", headers=teacher_h)
    assert listed.status_code == 200, listed.text
    rows = [row for row in listed.json().get("data", []) if row.get("notification_kind") == "score_grade_appeal"]
    assert rows
    assert any(row.get("appeal_status") == "pending" for row in rows)
