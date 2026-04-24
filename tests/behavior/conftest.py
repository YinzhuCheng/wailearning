"""
Shared fixtures for deferred multi-actor LLM behavior tests.

Skipping is applied via pytest_collection_modifyitems so all tests under
tests/behavior/ are skipped until the next round implements them.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        if "/behavior/" in str(item.path).replace("\\", "/"):
            item.add_marker(
                pytest.mark.skip(
                    reason="Behavior/E2E skeleton — implement and remove this hook or marker next round."
                )
            )


@pytest.fixture(scope="session")
def behavior_base_url() -> str:
    """Frontend origin for Playwright (next round). Override via env or pytest option."""
    return "http://127.0.0.1:5174"


@pytest.fixture(scope="session")
def behavior_api_base_url() -> str:
    """API base for direct HTTP steps alongside UI (next round)."""
    return "http://127.0.0.1:8001/api"
