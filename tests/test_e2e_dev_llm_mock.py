"""E2E dev mock LLM + manual grading drain."""

from __future__ import annotations

from unittest import mock
from urllib.parse import urlparse

import httpx
from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import LLMEndpointPreset
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
