"""Ephemeral test data and mock integrations for Playwright / local E2E."""

from __future__ import annotations

import json
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.config import settings
from app.database import get_db
from app.llm_grading import process_next_grading_task, start_grading_worker, worker_manager
from app.models import (
    Class,
    CourseEnrollment,
    CourseMaterial,
    CourseMaterialChapter,
    CourseMaterialSection,
    Gender,
    Homework,
    HomeworkGradingTask,
    LLMEndpointPreset,
    Student,
    Subject,
    User,
    UserRole,
)

router = APIRouter(prefix="/api/e2e", tags=["e2e-dev"])

_mock_llm_lock = threading.Lock()
_mock_llm_profiles: dict[str, dict[str, Any]] = {}


def _reset_mock_llm_state() -> None:
    with _mock_llm_lock:
        _mock_llm_profiles.clear()


def _record_mock_llm_request(profile: str, record: dict[str, Any]) -> None:
    with _mock_llm_lock:
        slot = _mock_llm_profiles.setdefault(profile, {"steps": [], "cursor": 0, "repeat_last": True, "requests": []})
        requests = slot.setdefault("requests", [])
        record["request_index"] = len(requests) + 1
        requests.append(record)
        if len(requests) > 200:
            del requests[:-200]


def _next_mock_llm_step(profile: str) -> dict[str, Any]:
    with _mock_llm_lock:
        slot = _mock_llm_profiles.setdefault(profile, {"steps": [], "cursor": 0, "repeat_last": True, "requests": []})
        steps = list(slot.get("steps") or [])
        cursor = int(slot.get("cursor") or 0)
        repeat_last = bool(slot.get("repeat_last", True))
        if not steps:
            step = {"kind": "ok", "score": 80.0, "comment": f"{profile}:ok"}
        elif cursor < len(steps):
            step = dict(steps[cursor] or {})
            slot["cursor"] = cursor + 1
        elif repeat_last:
            step = dict(steps[-1] or {})
        else:
            step = {"kind": "ok", "score": 80.0, "comment": f"{profile}:default"}
        return step


def _is_validation_request(payload: dict[str, Any]) -> bool:
    messages = payload.get("messages") or []
    if not messages:
        return False
    first = messages[0]
    content = first.get("content")
    if isinstance(content, str):
        return "single word: OK" in content or "reply with OK" in content
    if isinstance(content, list):
        joined = " ".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
        return "reply with OK" in joined
    return False


def _mock_llm_success_body(profile: str, step: dict[str, Any], *, validation: bool) -> dict[str, Any]:
    if validation:
        content = str(step.get("text") or "OK")
    else:
        payload = {
            "score": float(step.get("score", 80.0)),
            "comment": str(step.get("comment") or f"{profile}:ok"),
        }
        content = json.dumps(payload, ensure_ascii=False)
    usage = step.get("usage") or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    return {
        "choices": [{"message": {"content": content}}],
        "usage": usage,
    }


def _require_seed_token(x_e2e_seed_token: str | None) -> None:
    if not settings.E2E_DEV_SEED_ENABLED:
        raise HTTPException(status_code=404, detail="E2E dev seed is disabled.")
    expected = (settings.E2E_DEV_SEED_TOKEN or "").strip()
    if not expected or (x_e2e_seed_token or "").strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid E2E seed token.")


@router.post("/dev/reset-scenario")
def reset_e2e_scenario(
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create isolated users/classes/courses for UI tests. Safe to call repeatedly (new suffix each time).
    """
    _require_seed_token(x_e2e_seed_token)
    _reset_mock_llm_state()

    suffix = uuid.uuid4().hex[:10]
    pwd = "E2eTest1!"
    hpwd = get_password_hash(pwd)

    c1 = Class(name=f"E2E甲班_{suffix}", grade=2026)
    c2 = Class(name=f"E2E乙班_{suffix}", grade=2026)
    db.add_all([c1, c2])
    db.flush()

    admin = User(
        username=f"e2e_adm_{suffix}",
        hashed_password=get_password_hash("E2eAdmin1!"),
        real_name="E2E管理员",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    t_own = User(
        username=f"e2e_teach_own_{suffix}",
        hashed_password=hpwd,
        real_name=f"E2E任课甲_{suffix}",
        role=UserRole.TEACHER.value,
        is_active=True,
    )
    t_other = User(
        username=f"e2e_teach_other_{suffix}",
        hashed_password=hpwd,
        real_name=f"E2E任课乙_{suffix}",
        role=UserRole.TEACHER.value,
        is_active=True,
    )
    ct = User(
        username=f"e2e_class_teacher_{suffix}",
        hashed_password=hpwd,
        real_name=f"E2E班主任_{suffix}",
        role=UserRole.CLASS_TEACHER.value,
        class_id=c1.id,
        is_active=True,
    )
    db.add_all([admin, t_own, t_other, ct])
    db.flush()

    st_plain = Student(
        name="E2E学生甲",
        student_no=f"e2e_stu_plain_{suffix}",
        gender=Gender.MALE,
        class_id=c1.id,
    )
    st_drop = Student(
        name="E2E退选生",
        student_no=f"e2e_stu_drop_{suffix}",
        gender=Gender.MALE,
        class_id=c1.id,
    )
    st_b = Student(
        name="E2E学生乙",
        student_no=f"e2e_stu_b_{suffix}",
        gender=Gender.FEMALE,
        class_id=c1.id,
    )
    db.add_all([st_plain, st_drop, st_b])
    db.flush()

    u_plain = User(
        username=st_plain.student_no,
        hashed_password=hpwd,
        real_name=st_plain.name,
        role=UserRole.STUDENT.value,
        class_id=c1.id,
        is_active=True,
    )
    u_drop = User(
        username=st_drop.student_no,
        hashed_password=hpwd,
        real_name=st_drop.name,
        role=UserRole.STUDENT.value,
        class_id=c1.id,
        is_active=True,
    )
    u_b = User(
        username=st_b.student_no,
        hashed_password=hpwd,
        real_name=st_b.name,
        role=UserRole.STUDENT.value,
        class_id=c1.id,
        is_active=True,
    )
    db.add_all([u_plain, u_drop, u_b])
    db.flush()

    st_plain.parent_code = f"P{suffix[:6].upper()}"
    st_plain.parent_code_expires = None

    db.flush()
    course_req = Subject(
        name=f"E2E必修课_{suffix}",
        teacher_id=t_own.id,
        class_id=c1.id,
        course_type="required",
        status="active",
    )
    course_el = Subject(
        name=f"E2E选修课_{suffix}",
        teacher_id=t_own.id,
        class_id=c1.id,
        course_type="elective",
        status="active",
    )
    course_other = Subject(
        name=f"E2E乙班课_{suffix}",
        teacher_id=t_other.id,
        class_id=c2.id,
        course_type="required",
        status="active",
    )
    course_orphan = Subject(
        name=f"E2E无班级课_{suffix}",
        teacher_id=t_own.id,
        class_id=None,
        course_type="required",
        status="active",
    )
    db.add_all([course_req, course_el, course_other, course_orphan])
    db.flush()

    # st_plain / st_drop 已在必修课；st_b 仅在花名册，用于「从花名册进课」勾选
    for st in (st_plain, st_drop):
        db.add(
            CourseEnrollment(
                subject_id=course_req.id,
                student_id=st.id,
                class_id=c1.id,
                enrollment_type="required",
                can_remove=False,
            )
        )

    hw = Homework(
        title=f"E2E_UI作业_{suffix}",
        content="用于 Playwright UI 测试的作业说明。",
        class_id=c1.id,
        subject_id=course_req.id,
        max_score=100.0,
        grade_precision="integer",
        auto_grading_enabled=True,
        allow_late_submission=True,
        late_submission_affects_score=False,
        created_by=t_own.id,
    )
    db.add(hw)
    db.flush()

    unc = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == course_req.id,
            CourseMaterialChapter.is_uncategorized.is_(True),
        )
        .first()
    )
    if not unc:
        unc = CourseMaterialChapter(
            subject_id=course_req.id,
            parent_id=None,
            title="未分类",
            sort_order=0,
            is_uncategorized=True,
        )
        db.add(unc)
        db.flush()

    mat_disc = CourseMaterial(
        title=f"E2E讨论资料_{suffix}",
        content="用于讨论区 E2E 的资料正文。",
        class_id=c1.id,
        subject_id=course_req.id,
        created_by=t_own.id,
    )
    db.add(mat_disc)
    db.flush()
    db.add(
        CourseMaterialSection(
            material_id=mat_disc.id,
            chapter_id=unc.id,
            sort_order=0,
        )
    )

    db.commit()
    db.refresh(mat_disc)

    return {
        "suffix": suffix,
        "password_teacher_student": pwd,
        "password_admin": "E2eAdmin1!",
        "admin": {"username": admin.username, "password": "E2eAdmin1!"},
        "teacher_own": {"username": t_own.username, "password": pwd},
        "teacher_other": {"username": t_other.username, "password": pwd},
        "student_plain": {"username": u_plain.username, "password": pwd, "student_row_id": st_plain.id},
        "student_drop": {"username": u_drop.username, "password": pwd, "student_row_id": st_drop.id},
        "student_b": {"username": u_b.username, "password": pwd, "student_row_id": st_b.id},
        "class_id_1": c1.id,
        "class_id_2": c2.id,
        "class_name_1": c1.name,
        "course_required_id": course_req.id,
        "course_elective_id": course_el.id,
        "course_other_teacher_id": course_other.id,
        "course_orphan_id": course_orphan.id,
        "homework_id": hw.id,
        "material_discussion_id": mat_disc.id,
        "user_ids_for_batch": [u_plain.id, u_b.id],
        "teacher_user_id": t_own.id,
        "class_teacher": {"username": ct.username, "password": pwd},
        "parent_code": st_plain.parent_code,
    }


@router.post("/dev/mock-llm/configure")
def configure_mock_llm(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
) -> dict[str, Any]:
    _require_seed_token(x_e2e_seed_token)
    profiles = payload.get("profiles")
    if not isinstance(profiles, dict):
        raise HTTPException(status_code=400, detail="profiles must be an object.")
    with _mock_llm_lock:
        _mock_llm_profiles.clear()
        for profile, cfg in profiles.items():
            row = cfg if isinstance(cfg, dict) else {}
            _mock_llm_profiles[str(profile)] = {
                "steps": list(row.get("steps") or []),
                "cursor": 0,
                "repeat_last": bool(row.get("repeat_last", True)),
                "requests": [],
            }
    return {"profiles": sorted(_mock_llm_profiles.keys())}


@router.get("/dev/mock-llm/state")
def mock_llm_state(
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
) -> dict[str, Any]:
    _require_seed_token(x_e2e_seed_token)
    with _mock_llm_lock:
        return {
            "profiles": {
                name: {
                    "cursor": int(cfg.get("cursor") or 0),
                    "repeat_last": bool(cfg.get("repeat_last", True)),
                    "steps": list(cfg.get("steps") or []),
                    "requests": list(cfg.get("requests") or []),
                }
                for name, cfg in _mock_llm_profiles.items()
            }
        }


@router.get("/dev/grading-state")
def grading_state_for_e2e(
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_seed_token(x_e2e_seed_token)
    rows = (
        db.query(HomeworkGradingTask.status, func.count(HomeworkGradingTask.id))
        .group_by(HomeworkGradingTask.status)
        .all()
    )
    counts = {str(status or "unknown"): int(count or 0) for status, count in rows}
    return {
        "worker": {
            "enabled": bool(settings.ENABLE_LLM_GRADING_WORKER),
            "leader_only": bool(settings.LLM_GRADING_WORKER_LEADER),
            "running": worker_manager.is_running(),
            "poll_seconds": int(settings.LLM_GRADING_WORKER_POLL_SECONDS or 0),
        },
        "tasks": {
            "queued": counts.get("queued", 0),
            "processing": counts.get("processing", 0),
            "success": counts.get("success", 0),
            "failed": counts.get("failed", 0),
            "total": sum(counts.values()),
        },
    }


@router.post("/dev/worker")
def control_worker_for_e2e(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
) -> dict[str, Any]:
    _require_seed_token(x_e2e_seed_token)
    action = str(payload.get("action") or "status").strip().lower()
    if action == "start":
        if not settings.ENABLE_LLM_GRADING_WORKER:
            return {"ok": False, "action": action, "running": False, "detail": "worker disabled by settings"}
        start_grading_worker()
    elif action == "stop":
        worker_manager.stop()
    elif action != "status":
        raise HTTPException(status_code=400, detail="action must be one of: start, stop, status")
    return {"ok": True, "action": action, "running": worker_manager.is_running()}


@router.post("/dev/process-grading")
def process_grading_tasks_for_e2e(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
) -> dict[str, Any]:
    _require_seed_token(x_e2e_seed_token)
    max_tasks = int(payload.get("max_tasks") or 1)
    max_tasks = max(0, min(max_tasks, 50))
    processed = 0
    for _ in range(max_tasks):
        if not process_next_grading_task():
            break
        processed += 1
    return {"processed": processed}


@router.post("/dev/mark-preset-validated")
def mark_preset_validated_for_e2e(
    payload: dict[str, Any] = Body(default_factory=dict),
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_seed_token(x_e2e_seed_token)
    preset_id = payload.get("preset_id")
    try:
        preset_id = int(preset_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="preset_id must be an integer.") from exc
    preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Endpoint preset not found.")
    preset.validation_status = "validated"
    preset.validation_message = str(payload.get("validation_message") or "e2e dev forced validated")
    preset.text_validation_status = "passed"
    preset.text_validation_message = "e2e dev forced validated"
    preset.vision_validation_status = "passed"
    preset.vision_validation_message = "e2e dev forced validated"
    preset.supports_vision = True
    preset.validated_at = datetime.now(timezone.utc)
    db.commit()
    return {"id": preset.id, "validation_status": preset.validation_status, "supports_vision": preset.supports_vision}


@router.post("/dev/mock-llm/{profile}/v1/chat/completions")
async def mock_llm_chat_completions(
    profile: str,
    request: Request,
):
    if not settings.E2E_DEV_SEED_ENABLED:
        raise HTTPException(status_code=404, detail="E2E dev seed is disabled.")
    try:
        payload = await request.json()
    except Exception as exc:  # pragma: no cover - malformed request path
        raise HTTPException(status_code=400, detail=f"invalid json body: {exc}") from exc

    validation = _is_validation_request(payload if isinstance(payload, dict) else {})
    step = _next_mock_llm_step(profile)
    kind = str(step.get("kind") or "ok").strip().lower()
    sleep_seconds = float(step.get("sleep_seconds") or 0.0)
    _record_mock_llm_request(
        profile,
        {
            "kind": kind,
            "validation": validation,
            "model": payload.get("model"),
            "max_tokens": payload.get("max_tokens"),
            "sleep_seconds": sleep_seconds,
            "ts": time.time(),
        },
    )

    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    if kind in {"timeout", "sleep_then_ok"}:
        body = _mock_llm_success_body(profile, step, validation=validation)
        return JSONResponse(body)
    if kind == "http_error":
        status_code = int(step.get("status_code") or 500)
        body = step.get("body")
        if isinstance(body, (dict, list)):
            return JSONResponse(body, status_code=status_code)
        return PlainTextResponse(str(body or f"{profile}:{status_code}"), status_code=status_code)
    if kind in {"invalid_json", "malformed_json"}:
        text_body = step.get("body")
        if text_body is None:
            text_body = '{"choices":[{"message":{"content":"not-json-comment"}}],"usage":{"prompt_tokens":10}}'
        return PlainTextResponse(str(text_body), media_type="application/json")
    if kind in {"empty_body", "empty_response_body"}:
        return PlainTextResponse("", media_type="application/json")
    if kind == "bad_grading_payload":
        body = {
            "choices": [{"message": {"content": str(step.get("content") or "plain text, not score json")}}],
            "usage": step.get("usage") or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        return JSONResponse(body)
    if kind == "empty_message":
        body = {
            "choices": [{"message": {"content": ""}}],
            "usage": step.get("usage") or {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        return JSONResponse(body)
    if kind == "rate_limit":
        body = step.get("body") or {"error": "rate limited"}
        return JSONResponse(body, status_code=int(step.get("status_code") or 429))

    body = _mock_llm_success_body(profile, step, validation=validation)
    return JSONResponse(body)
