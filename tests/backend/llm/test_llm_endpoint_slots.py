"""Unit tests for per-preset outbound slots (process-local semaphores)."""

from unittest import mock

from app.llm_endpoint_slots import (
    note_preset_rate_limited,
    preset_in_cooldown,
    release_preset_slot,
    try_acquire_preset_slot,
)
from app.llm_group_routing import _GroupState


class _FakeLink:
    def __init__(self, id_: int, priority: int = 1) -> None:
        self.id = id_
        self.priority = priority
        self.group_id = 1
        self.preset_id = id_


def test_rotate_head_to_end():
    a, b, c = _FakeLink(1), _FakeLink(2), _FakeLink(3)
    gs = _GroupState(base_order=[a, b, c], current_order=[a, b, c])
    gs.rotate_head_to_end()
    assert [x.id for x in gs.current_order] == [2, 3, 1]


def test_preset_slot_limit_blocks_second_acquire():
    with mock.patch("app.llm_endpoint_slots.settings") as s:
        s.LLM_PRESET_MAX_CONCURRENT_REQUESTS = 1
        s.LLM_PRESET_COOLDOWN_AFTER_429_SECONDS = 0
        s.LLM_PRESET_SLOT_WAIT_SECONDS = 0.01
        s.LLM_PRESET_SLOT_BLOCK_SECONDS = 0.05
        import app.llm_endpoint_slots as slots

        slots._semaphores.clear()
        slots._cooldown_until.clear()
        assert try_acquire_preset_slot(9001) is True
        assert try_acquire_preset_slot(9001) is False
        release_preset_slot(9001)
        assert try_acquire_preset_slot(9001) is True
        release_preset_slot(9001)


def test_rate_limit_sets_cooldown():
    with mock.patch("app.llm_endpoint_slots.settings") as s:
        s.LLM_PRESET_MAX_CONCURRENT_REQUESTS = 1
        s.LLM_PRESET_COOLDOWN_AFTER_429_SECONDS = 60.0
        s.LLM_PRESET_SLOT_WAIT_SECONDS = 0.01
        import app.llm_endpoint_slots as slots

        slots._semaphores.clear()
        slots._cooldown_until.clear()
        note_preset_rate_limited(42)
        assert preset_in_cooldown(42) is True
