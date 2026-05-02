"""
Per-preset outbound concurrency gates + short cooldown after HTTP 429.

Limits how many in-flight HTTP calls each LLMEndpointPreset may have per worker process.
When a preset is at capacity or cooling down after rate-limit, routing rotates to the next
member in the same group before blocking.

Redis-free: uses threading.Semaphore in-process (aligned with the existing ThreadPoolExecutor worker).
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from app.config import settings

_lock = threading.Lock()
_semaphores: dict[int, threading.Semaphore] = {}
_cooldown_until: dict[int, float] = {}


def _limit_for_preset(preset_id: int) -> int:
    return max(0, int(settings.LLM_PRESET_MAX_CONCURRENT_REQUESTS or 0))


def _get_semaphore(preset_id: int) -> Optional[threading.Semaphore]:
    lim = _limit_for_preset(preset_id)
    if lim <= 0:
        return None
    with _lock:
        if preset_id not in _semaphores:
            _semaphores[preset_id] = threading.Semaphore(lim)
        return _semaphores[preset_id]


def preset_in_cooldown(preset_id: int) -> bool:
    until = _cooldown_until.get(int(preset_id))
    if until is None:
        return False
    if time.monotonic() >= until:
        try:
            del _cooldown_until[int(preset_id)]
        except KeyError:
            pass
        return False
    return True


def note_preset_rate_limited(preset_id: int) -> None:
    sec = float(settings.LLM_PRESET_COOLDOWN_AFTER_429_SECONDS or 0)
    if sec <= 0:
        return
    _cooldown_until[int(preset_id)] = time.monotonic() + sec


def try_acquire_preset_slot(preset_id: int) -> bool:
    """Non-blocking: False if at capacity, in cooldown, or semaphore unavailable."""
    pid = int(preset_id)
    if preset_in_cooldown(pid):
        return False
    sem = _get_semaphore(pid)
    if sem is None:
        return True
    return sem.acquire(blocking=False)


def release_preset_slot(preset_id: int) -> None:
    pid = int(preset_id)
    sem = _get_semaphore(pid)
    if sem is None:
        return
    try:
        sem.release()
    except ValueError:
        pass


def blocking_acquire_preset_slot(preset_id: int, *, timeout_seconds: float) -> bool:
    """
    Wait until a slot is available or timeout. Returns False on timeout.
    Unlimited presets (limit<=0) always return True without blocking.
    """
    pid = int(preset_id)
    deadline = time.monotonic() + max(0.0, float(timeout_seconds))
    wait_tick = min(0.25, max(0.02, float(settings.LLM_PRESET_SLOT_WAIT_SECONDS or 0.05)))
    while True:
        now = time.monotonic()
        if now >= deadline:
            return False
        if preset_in_cooldown(pid):
            time.sleep(min(wait_tick, deadline - now))
            continue
        sem = _get_semaphore(pid)
        if sem is None:
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        if sem.acquire(timeout=min(0.35, remaining)):
            return True
