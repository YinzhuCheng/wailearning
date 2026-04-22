"""Pytest configuration: set env before any app module imports DATABASE_URL/engine."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Fresh SQLite file per test process (avoid clobbering dev DB or parallel workers).
_tmp = Path(tempfile.mkdtemp(prefix="bimsa_llm_test_")) / "api.sqlite"
_sqlite_url = "sqlite:///" + str(_tmp.resolve())

os.environ["DATABASE_URL"] = _sqlite_url
os.environ["ENABLE_LLM_GRADING_WORKER"] = "false"
os.environ["LLM_GRADING_WORKER_LEADER"] = "false"
os.environ["INIT_DEFAULT_DATA"] = "false"
os.environ["SECRET_KEY"] = "test-secret-key-llm-settings-api"
# Starlette TestClient uses host "testserver"; app TrustedHostMiddleware must allow it.
os.environ["TRUSTED_HOSTS"] = "localhost,127.0.0.1,testserver"
