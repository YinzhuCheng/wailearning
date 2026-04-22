"""Pytest: configure env before importing app (database, worker, test hooks)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="bimsa_pytest_")) / "test.sqlite"
_sqlite_url = "sqlite:///" + str(_tmp.resolve())

os.environ["DATABASE_URL"] = _sqlite_url
os.environ["ENABLE_LLM_GRADING_WORKER"] = "false"
os.environ["LLM_GRADING_WORKER_LEADER"] = "false"
os.environ["INIT_DEFAULT_DATA"] = "false"
os.environ["SECRET_KEY"] = "pytest-secret-key-homework-llm"
os.environ["TRUSTED_HOSTS"] = "localhost,127.0.0.1,testserver"
os.environ["LLM_GRADING_TEST_SKIP_BACKOFF"] = "1"
