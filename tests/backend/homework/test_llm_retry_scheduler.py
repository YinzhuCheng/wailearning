from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest import mock

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.backend.courseeval_backend.db.database import SessionLocal
from apps.backend.courseeval_backend.db.models import HomeworkGradingTask, LLMTokenUsageLog
from apps.backend.courseeval_backend.domains.llm.runtime import advance_test_clock, set_test_clock
from apps.backend.courseeval_backend.llm_grading import claim_grading_tasks_batch, process_grading_task
from apps.backend.courseeval_backend.main import app
from tests.scenarios.llm_scenario import json_llm_response, login_api, make_grading_course_with_homework


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def _reset_db():
    from tests.db_reset import reset_test_database_schema

    reset_test_database_schema()
    from apps.backend.courseeval_backend.bootstrap import ensure_schema_updates

    ensure_schema_updates()
    yield
    SessionLocal().close()


def test_grading_task_transient_failure_becomes_retry_scheduled_then_succeeds(client: TestClient):
    ctx = make_grading_course_with_homework(preset_max_retries=0)
    student_h = login_api(client, ctx["student_username"], ctx["student_password"])
    set_test_clock(datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc))

    r = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_h,
        json={"content": "retry later"},
    )
    assert r.status_code == 200, r.text

    db = SessionLocal()
    try:
        tid = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first().id
    finally:
        db.close()

    with mock.patch.object(httpx.Client, "post", lambda self, url, **kwargs: httpx.Response(503, json={"error": "upstream"})):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task is not None
        assert task.status == "retry_scheduled"
        assert task.failure_class == "transient"
        assert task.retry_count == 1
        assert task.next_retry_at is not None
        assert task.finished_at is None
        assert db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == tid).count() == 0
    finally:
        db.close()

    advance_test_clock(timedelta(seconds=59))
    assert claim_grading_tasks_batch(1) == []

    advance_test_clock(timedelta(seconds=1))
    claimed = claim_grading_tasks_batch(1)
    assert claimed == [tid]

    with mock.patch.object(
        httpx.Client,
        "post",
        lambda self, url, **kwargs: httpx.Response(200, json=json_llm_response(83.0, "recovered")),
    ):
        process_grading_task(tid)

    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == tid).first()
        assert task is not None
        assert task.status == "success"
        assert task.error_code is None
        assert task.next_retry_at is None
        assert db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == tid).count() == 1
    finally:
        db.close()
