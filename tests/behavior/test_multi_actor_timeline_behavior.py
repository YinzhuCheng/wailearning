"""
M1–M5: Multi-user / multi-role interleaved timelines (teacher ‖ student ‖ admin).

Execution deferred — see tests/behavior/conftest.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ActorSession:
    """Holds cookies / storage state for one browser context (next round)."""
    role: str
    user_label: str


class TimelineRunner:
    """Ordered steps with optional wait conditions (next round: asyncio + Playwright)."""

    def __init__(self) -> None:
        self._steps: list[tuple[str, Callable[[], None]]] = []

    def step(self, label: str, fn: Callable[[], None]) -> "TimelineRunner":
        self._steps.append((label, fn))
        return self

    def run(self) -> None:
        for _label, fn in self._steps:
            fn()


def test_m1_teacher_saves_config_between_two_student_submissions() -> None:
    """
    M1: T0 student A submits hw1 → T1 teacher saves LLM config → T2 student A submits hw2.
    Assert both tasks use post-T1 config (or document race if near-simultaneous).
    """
    _admin = ActorSession("admin", "admin")
    _teacher = ActorSession("teacher", "t1")
    _student_a = ActorSession("student", "a")

    TimelineRunner().step("T0 student A hw1", lambda: None).step("T1 teacher save", lambda: None).step(
        "T2 student A hw2", lambda: None
    ).run()
    del _admin, _teacher, _student_a


def test_m2_two_students_parallel_grading_under_cap_three() -> None:
    """
    M2: max_parallel_grading_tasks=2; students A and B submit simultaneously;
    at most 2 processing; both complete or explicit failure; per-student usage independent.
    """
    TimelineRunner().step("set parallel 2", lambda: None).step("A submit", lambda: None).step("B submit", lambda: None).run()


def test_m3_admin_lowers_cap_while_task_processing() -> None:
    """
    M3: Task in processing (slow LLM mock) → admin lowers student daily cap;
    in-flight completes; new task precheck uses new cap.
    """
    TimelineRunner().step("start slow grade", lambda: None).step("admin lower cap", lambda: None).step("new submit", lambda: None).run()


def test_m4_admin_changes_parallel_while_queue_backed_up() -> None:
    """
    M4: Queue 5 tasks; parallel=3 → observe batch; immediately parallel=1 → next claim size 1.
    """
    TimelineRunner().step("seed queue", lambda: None).step("parallel 3", lambda: None).step("parallel 1", lambda: None).run()


def test_m5_concurrent_admin_and_teacher_sessions() -> None:
    """
    M5: Two browsers: admin changes global policy while teacher edits course LLM;
    no 500; last-write-wins per resource documented in assertions.
    """
    _sessions: list[ActorSession] = [ActorSession("admin", "a"), ActorSession("teacher", "t")]
    TimelineRunner().step("concurrent edits", lambda: None).run()
    del _sessions
