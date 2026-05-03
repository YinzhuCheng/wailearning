"""E2E dev seed endpoint (disabled by default)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.core.config import settings
from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine
from apps.backend.wailearning_backend.main import app
from apps.backend.wailearning_backend.db.models import User, UserRole


@pytest.fixture(autouse=True)
def _reset_e2e_settings():
    yield
    settings.E2E_DEV_SEED_ENABLED = False
    settings.E2E_DEV_SEED_TOKEN = ""


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
    from apps.backend.wailearning_backend.bootstrap import ensure_schema_updates

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


@pytest.mark.parametrize(
    ("enabled", "configured_token", "request_token", "expected_status"),
    [
        (False, "", "any", 404),
        (True, "secret-xyz", "wrong", 403),
    ],
)
def test_e2e_seed_rejects_disabled_or_wrong_token(
    client: TestClient, enabled: bool, configured_token: str, request_token: str, expected_status: int
):
    settings.E2E_DEV_SEED_ENABLED = enabled
    settings.E2E_DEV_SEED_TOKEN = configured_token
    r = client.post("/api/e2e/dev/reset-scenario", headers={"X-E2E-Seed-Token": request_token})
    assert r.status_code == expected_status


def test_e2e_seed_ok_when_enabled(client: TestClient):
    settings.E2E_DEV_SEED_ENABLED = True
    settings.E2E_DEV_SEED_TOKEN = "tok-e2e-1"
    r = client.post("/api/e2e/dev/reset-scenario", headers={"X-E2E-Seed-Token": "tok-e2e-1"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "suffix" in body
    assert "course_required_id" in body
