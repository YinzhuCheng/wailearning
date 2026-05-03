"""Shared fixtures for API-level LLM behavior tests under tests/behavior/."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from apps.backend.wailearning_backend.db.database import Base, SessionLocal, engine


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
    yield
    SessionLocal().close()


@pytest.fixture
def client() -> TestClient:
    from apps.backend.wailearning_backend.main import app

    return TestClient(app)


@pytest.fixture(scope="session")
def behavior_base_url() -> str:
    """Reserved for future Playwright runs; API tests use TestClient."""
    return "http://127.0.0.1:5174"


@pytest.fixture(scope="session")
def behavior_api_base_url() -> str:
    return "http://127.0.0.1:8001/api"
