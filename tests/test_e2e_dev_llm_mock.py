"""E2E dev mock LLM + manual grading drain."""

from __future__ import annotations

import time
from unittest import mock
from urllib.parse import urlparse

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.llm_grading import RetryableLLMError, worker_manager
from app.main import app
from app.models import HomeworkGradingTask, LLMEndpointPreset
from app.bootstrap import _backfill_default_llm_groups_for_existing_configs
from tests.llm_scenario import ensure_admin, login_api, make_grading_course_with_homework


def _tiny_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x04\x00\x00\x00"
        b"\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff\x1f\x00\x02\xeb\x01\xf5"
        b"\x69G\xd3/\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_mock_llm_configure_state_and_manual_process():
    ensure_admin()
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "tok-e2e-mock"
    client = TestClient(app)

    cfg = client.post(
        "/api/e2e/dev/mock-llm/configure",
        headers={"X-E2E-Seed-Token": "tok-e2e-mock"},
        json={
            "profiles": {
                "grade_ok": {
                    "steps": [{"kind": "ok", "score": 84.0, "comment": "mock pass"}],
                    "repeat_last": True,
                }
            }
        },
    )
    assert cfg.status_code == 200, cfg.text

    state = client.get(
        "/api/e2e/dev/mock-llm/state",
        headers={"X-E2E-Seed-Token": "tok-e2e-mock"},
    )
    assert state.status_code == 200, state.text
    assert "grade_ok" in state.json()["profiles"]

    ctx = make_grading_course_with_homework()
    db = SessionLocal()
    try:
        preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == ctx["preset_id"]).first()
        assert preset is not None
        preset.base_url = "http://testserver/api/e2e/dev/mock-llm/grade_ok/v1/"
        preset.connect_timeout_seconds = 1
        preset.read_timeout_seconds = 2
        db.commit()
    finally:
        db.close()

    student_headers = login_api(client, ctx["student_username"], ctx["student_password"])
    db = SessionLocal()
    try:
        preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == ctx["preset_id"]).first()
        assert preset is not None
        preset.validation_status = "validated"
        preset.validation_message = "seeded for e2e dev mock"
        preset.supports_vision = True
        db.commit()
    finally:
        db.close()
    _backfill_default_llm_groups_for_existing_configs()

    sub = client.post(
        f"/api/homeworks/{ctx['homework_id']}/submission",
        headers=student_headers,
        json={"content": "mock-e2e"},
    )
    assert sub.status_code == 200, sub.text
    assert sub.json()["latest_task_status"] in ("queued", "processing", "success")

    original_post = httpx.Client.post

    def _relay_mock_llm(self, url, **kwargs):
        if not isinstance(url, str) or not url.startswith("http://testserver/"):
            return original_post(self, url, **kwargs)
        parsed = urlparse(url)
        relayed = client.post(
            parsed.path,
            json=kwargs.get("json"),
            headers={
                "Authorization": (kwargs.get("headers") or {}).get("Authorization", ""),
                "Content-Type": "application/json",
            },
        )
        return httpx.Response(relayed.status_code, content=relayed.content, headers=relayed.headers)

    with mock.patch.object(httpx.Client, "post", _relay_mock_llm):
        drain = client.post(
            "/api/e2e/dev/process-grading",
            headers={"X-E2E-Seed-Token": "tok-e2e-mock"},
            json={"max_tasks": 3},
        )
    assert drain.status_code == 200, drain.text
    assert drain.json()["processed"] >= 1

    hist = client.get(f"/api/homeworks/{ctx['homework_id']}/submission/me/history", headers=student_headers)
    assert hist.status_code == 200, hist.text
    assert hist.json()["summary"]["latest_task_status"] == "success"
    assert hist.json()["summary"]["review_score"] == 84.0

    state2 = client.get(
        "/api/e2e/dev/mock-llm/state",
        headers={"X-E2E-Seed-Token": "tok-e2e-mock"},
    )
    assert state2.status_code == 200, state2.text
    assert len(state2.json()["profiles"]["grade_ok"]["requests"]) >= 1

    settings.E2E_DEV_SEED_ENABLED = False
    settings.E2E_DEV_SEED_TOKEN = ""


def test_mock_llm_empty_body_and_malformed_json_state():
    ensure_admin()
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "tok-e2e-mock"
    client = TestClient(app)

    cfg = client.post(
        "/api/e2e/dev/mock-llm/configure",
        headers={"X-E2E-Seed-Token": "tok-e2e-mock"},
        json={
            "profiles": {
                "empty_body": {"steps": [{"kind": "empty_body"}], "repeat_last": True},
                "malformed": {"steps": [{"kind": "malformed_json", "body": "{"}], "repeat_last": True},
            }
        },
    )
    assert cfg.status_code == 200, cfg.text

    empty = client.post("/api/e2e/dev/mock-llm/empty_body/v1/chat/completions", json={"messages": []})
    assert empty.status_code == 200
    assert empty.text == ""

    malformed = client.post("/api/e2e/dev/mock-llm/malformed/v1/chat/completions", json={"messages": []})
    assert malformed.status_code == 200
    assert malformed.text == "{"

    state = client.get(
        "/api/e2e/dev/mock-llm/state",
        headers={"X-E2E-Seed-Token": "tok-e2e-mock"},
    )
    assert state.status_code == 200, state.text
    assert state.json()["profiles"]["empty_body"]["requests"][0]["request_index"] == 1
    assert state.json()["profiles"]["malformed"]["requests"][0]["kind"] == "malformed_json"

    settings.E2E_DEV_SEED_ENABLED = False
    settings.E2E_DEV_SEED_TOKEN = ""


def test_e2e_worker_status_and_control():
    ensure_admin()
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "tok-e2e-worker"
    settings.ENABLE_LLM_GRADING_WORKER = True
    settings.LLM_GRADING_WORKER_LEADER = True
    settings.LLM_GRADING_WORKER_POLL_SECONDS = 0
    worker_manager.stop()
    client = TestClient(app)

    status_before = client.get(
        "/api/e2e/dev/grading-state",
        headers={"X-E2E-Seed-Token": "tok-e2e-worker"},
    )
    assert status_before.status_code == 200, status_before.text
    assert status_before.json()["worker"]["running"] is False

    started = client.post(
        "/api/e2e/dev/worker",
        headers={"X-E2E-Seed-Token": "tok-e2e-worker"},
        json={"action": "start"},
    )
    assert started.status_code == 200, started.text
    assert started.json()["running"] is True

    ctx = make_grading_course_with_homework()
    student_headers = login_api(client, ctx["student_username"], ctx["student_password"])
    with mock.patch("app.llm_grading._request_grade_from_endpoint", side_effect=RetryableLLMError("worker-test-boom")):
        sub = client.post(
            f"/api/homeworks/{ctx['homework_id']}/submission",
            headers=student_headers,
            json={"content": "worker-control"},
        )
        assert sub.status_code == 200, sub.text

        for _ in range(80):
            db = SessionLocal()
            try:
                task = db.query(HomeworkGradingTask).order_by(HomeworkGradingTask.id.desc()).first()
                assert task is not None
                if task.status in {"failed", "success"}:
                    break
            finally:
                db.close()
            time.sleep(0.1)
        else:
            raise AssertionError("worker did not process queued task in time")

    state = client.get(
        "/api/e2e/dev/grading-state",
        headers={"X-E2E-Seed-Token": "tok-e2e-worker"},
    )
    assert state.status_code == 200, state.text
    task_counts = state.json()["tasks"]
    assert task_counts["total"] >= 1
    assert task_counts["failed"] + task_counts["queued"] + task_counts["processing"] >= 1

    stopped = client.post(
        "/api/e2e/dev/worker",
        headers={"X-E2E-Seed-Token": "tok-e2e-worker"},
        json={"action": "stop"},
    )
    assert stopped.status_code == 200, stopped.text
    assert stopped.json()["running"] is False

    settings.E2E_DEV_SEED_ENABLED = False
    settings.E2E_DEV_SEED_TOKEN = ""
    settings.ENABLE_LLM_GRADING_WORKER = False
    settings.LLM_GRADING_WORKER_LEADER = False
    settings.LLM_GRADING_WORKER_POLL_SECONDS = 2
