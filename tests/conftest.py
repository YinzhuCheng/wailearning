"""Pytest: configure env before importing app (database, worker, test hooks)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def _env_flag(name: str, default: bool) -> str:
    raw = os.environ.get(name)
    if raw is None:
        return "true" if default else "false"
    return "true" if raw.strip().lower() in {"1", "true", "yes", "on"} else "false"


_tmp_dir = Path(__file__).resolve().parents[1] / ".pytest_tmp"
_tmp_dir.mkdir(exist_ok=True)
_tmp = _tmp_dir / "test.sqlite"
_sqlite_url = "sqlite:///" + _tmp.resolve().as_posix()
_database_url = os.environ.get("TEST_DATABASE_URL", "").strip() or _sqlite_url

os.environ["DATABASE_URL"] = _database_url
os.environ["ENABLE_LLM_GRADING_WORKER"] = _env_flag("TEST_ENABLE_LLM_GRADING_WORKER", False)
os.environ["LLM_GRADING_WORKER_LEADER"] = _env_flag("TEST_LLM_GRADING_WORKER_LEADER", False)
os.environ["INIT_DEFAULT_DATA"] = "false"
# Long enough for production-style REQUIRE_STRONG_SECRETS / APP_ENV=production validation.
os.environ["SECRET_KEY"] = "pytest-secret-key-homework-llm-" + ("x" * 40)
os.environ["TRUSTED_HOSTS"] = "localhost,127.0.0.1,testserver"
os.environ["LLM_GRADING_TEST_SKIP_BACKOFF"] = "1"

_DEFAULT_ENABLE_WORKER = os.environ["ENABLE_LLM_GRADING_WORKER"] == "true"
_DEFAULT_WORKER_LEADER = os.environ["LLM_GRADING_WORKER_LEADER"] == "true"


@pytest.fixture(autouse=True)
def _reset_worker_and_e2e_settings():
    from app.config import settings
    from app.llm_grading import worker_manager

    worker_manager.stop()
    settings.ENABLE_LLM_GRADING_WORKER = _DEFAULT_ENABLE_WORKER
    settings.LLM_GRADING_WORKER_LEADER = _DEFAULT_WORKER_LEADER
    settings.LLM_GRADING_WORKER_POLL_SECONDS = 2
    settings.E2E_DEV_SEED_ENABLED = False
    settings.E2E_DEV_SEED_TOKEN = ""
    yield
    worker_manager.stop()
    settings.ENABLE_LLM_GRADING_WORKER = _DEFAULT_ENABLE_WORKER
    settings.LLM_GRADING_WORKER_LEADER = _DEFAULT_WORKER_LEADER
    settings.LLM_GRADING_WORKER_POLL_SECONDS = 2
    settings.E2E_DEV_SEED_ENABLED = False
    settings.E2E_DEV_SEED_TOKEN = ""
