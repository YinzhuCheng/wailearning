"""Public registration guards when ALLOW_PUBLIC_REGISTRATION is enabled."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.backend.wailearning_backend.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_public_register_rejects_nonexistent_class_id(client: TestClient, monkeypatch):
    monkeypatch.setenv("ALLOW_PUBLIC_REGISTRATION", "true")
    from apps.backend.wailearning_backend.core.config import settings

    monkeypatch.setattr(settings, "ALLOW_PUBLIC_REGISTRATION", True)

    r = client.post(
        "/api/auth/register",
        json={
            "username": "orphan_reg_user_should_fail",
            "password": "ValidPass9!",
            "real_name": "x",
            "role": "student",
            "class_id": 999_999_991,
        },
    )
    assert r.status_code == 400
    assert "class" in (r.json().get("detail") or "").lower()
