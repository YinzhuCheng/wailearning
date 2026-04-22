"""
LLM group routing: priority across groups, weighted round-robin + adaptive order within each group.

Used by app.llm_grading to pick endpoints without calling the network; actual HTTP is in _request_grade_from_endpoint.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import CourseLLMConfigEndpoint, LLMEndpointPreset, LLMGroup

# Non-retryable auth: keep order; do not shift to end (same member would fail again).
NON_RETRYABLE_STATUS_CODES = {401, 403}


@dataclass
class _GroupState:
    base_order: list[CourseLLMConfigEndpoint]
    current_order: list[CourseLLMConfigEndpoint]
    next_rr_index: int = 0

    @classmethod
    def from_group(cls, group: "LLMGroup") -> Optional["_GroupState"]:
        members = [m for m in (group.members or []) if m is not None]
        if not members:
            return None
        ordered = sorted(members, key=lambda m: (m.priority, m.id))
        return cls(base_order=ordered, current_order=list(ordered), next_rr_index=0)

    def pick_start_index(self) -> int:
        if not self.current_order:
            return 0
        n = len(self.current_order)
        idx = self.next_rr_index % n
        self.next_rr_index = (self.next_rr_index + 1) % max(n, 1)
        return idx

    def rotate_to_start(self, start: int) -> list[CourseLLMConfigEndpoint]:
        if not self.current_order or start <= 0:
            return list(self.current_order)
        n = len(self.current_order)
        s = start % n
        return self.current_order[s:] + self.current_order[:s]

    def after_failed_attempt(
        self,
        link: CourseLLMConfigEndpoint,
        exc: Exception,
    ) -> None:
        if not self.current_order:
            return
        if self._should_move_to_end(exc):
            self._move_to_end(link)

    def _move_to_end(self, link: CourseLLMConfigEndpoint) -> None:
        matches = [x for x in self.current_order if x.id == link.id]
        if not matches:
            return
        for m in matches:
            self.current_order.remove(m)
            self.current_order.append(m)

    @staticmethod
    def _should_move_to_end(exc: Exception) -> bool:
        # Avoid importing app.llm_grading (circular); match by class name.
        name = type(exc).__name__
        if name == "RetryableLLMError":
            return True
        if name == "NonRetryableLLMError":
            text = str(exc)
            for code in NON_RETRYABLE_STATUS_CODES:
                if f"HTTP {code}" in text:
                    return False
            if "鉴权" in text or "权限" in text:
                return False
        return True


@dataclass
class GroupRoutingContext:
    """Holds per-task routing state; safe to use for one _grade_with_endpoint_group call."""

    group_states: list[_GroupState] = field(default_factory=list)
    task_id: int = 0
    _artifact: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_config(cls, group_rows: list["LLMGroup"], *, task_id: int) -> "GroupRoutingContext":
        states: list[_GroupState] = []
        for g in sorted(group_rows, key=lambda x: (x.priority, x.id)):
            st = _GroupState.from_group(g)
            if st:
                states.append(st)
        if not states:
            return cls(group_states=[], task_id=task_id, _artifact={})
        ctx = cls(group_states=states, task_id=task_id, _artifact={})
        random.seed((task_id << 8) ^ int(time.time() * 1000) & 0xFFFF)
        return ctx

    def routing_payload(self) -> dict[str, Any]:
        return {
            "version": 1,
            "mode": "groups",
            "status": "routing",
            "task_id": self.task_id,
            "groups": [
                {
                    "group_id": g.base_order[0].group_id if g.base_order else None,
                    "order_preset_ids": [m.preset_id for m in g.current_order],
                }
                for g in self.group_states
            ],
        }

    def build_artifact(self) -> dict[str, Any]:
        return {"llm_routing": self.routing_payload()}

    def iter_group_then_members(
        self,
    ) -> list[tuple[_GroupState, list[CourseLLMConfigEndpoint]]]:
        out: list[tuple[_GroupState, list[CourseLLMConfigEndpoint]]] = []
        for g in self.group_states:
            start = g.pick_start_index()
            order = g.rotate_to_start(start)
            out.append((g, order))
        return out

    def note_failure(self, group_state: _GroupState, link: CourseLLMConfigEndpoint, exc: Exception) -> None:
        group_state.after_failed_attempt(link, exc)
