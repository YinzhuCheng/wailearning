from __future__ import annotations

import base64
import io
import json
import os
import mimetypes
import re
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any, Optional
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import fitz
import httpx
from docx import Document
from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.attachments import get_attachment_file_path
from app.config import settings
from app.database import SessionLocal
from app.llm_group_routing import GroupRoutingContext
from app.models import (
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    Homework,
    HomeworkAttempt,
    HomeworkGradingTask,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMEndpointPreset,
    LLMGroup,
    LLMTokenUsageLog,
)

VISION_TEST_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAusB9Y9nKXUAAAAASUVORK5CYII="
)
JSON_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)
MAX_ZIP_DEPTH = 4
MAX_ZIP_FILES = 100
MAX_ZIP_TOTAL_BYTES = 80 * 1024 * 1024
MAX_FILE_TEXT_CHARS = 12000
MAX_IPYNB_OUTPUT_CHARS = 6000
SUPPORTED_TEXT_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".csv",
    ".doc",
    ".docx",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rb",
    ".rs",
    ".sql",
    ".tex",
    ".ts",
    ".tsx",
    ".txt",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
ZIP_EXTENSIONS = {".zip"}
IPYNB_EXTENSIONS = {".ipynb"}
PDF_EXTENSIONS = {".pdf"}
RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {401, 403}


@dataclass
class MaterialBlock:
    priority: int
    path: str
    block_type: str
    text: Optional[str] = None
    image_data_url: Optional[str] = None
    estimated_tokens: int = 0


class RetryableLLMError(Exception):
    pass


class NonRetryableLLMError(Exception):
    pass


class _WorkerManager:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def start(self) -> None:
        if not settings.ENABLE_LLM_GRADING_WORKER:
            return
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="llm-grading-worker", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = process_next_grading_task()
                if processed:
                    continue
            except Exception as exc:  # pragma: no cover - defensive background logging
                print(f"LLM grading worker loop error: {exc}")
            self._stop_event.wait(settings.LLM_GRADING_WORKER_POLL_SECONDS)


worker_manager = _WorkerManager()

# Serialize grading for a single task id in-process (duplicate worker wakeups / tests).
_task_grading_locks: dict[int, threading.Lock] = {}
_task_grading_locks_mutex = threading.Lock()


def _grading_lock_for_task(task_id: int) -> threading.Lock:
    with _task_grading_locks_mutex:
        if task_id not in _task_grading_locks:
            _task_grading_locks[task_id] = threading.Lock()
        return _task_grading_locks[task_id]


def start_grading_worker() -> None:
    worker_manager.start()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def normalize_score_for_homework(homework: Homework, score: float | int) -> float:
    value = max(0.0, min(float(score), float(homework.max_score or 100)))
    if (homework.grade_precision or "integer") == "decimal_1":
        return round(value, 1)
    return float(round(value))


def _teacher_candidate_sort_key(candidate: HomeworkScoreCandidate) -> tuple[float, datetime]:
    """Higher score first, then newer; used only among teacher rows."""
    ts = candidate.updated_at or candidate.created_at or datetime.min.replace(tzinfo=timezone.utc)
    return (float(candidate.score or 0), ts)


def _auto_candidate_sort_key(candidate: HomeworkScoreCandidate) -> tuple[float, datetime]:
    """Among auto rows: higher score, then newer."""
    ts = candidate.updated_at or candidate.created_at or datetime.min.replace(tzinfo=timezone.utc)
    return (float(candidate.score or 0), ts)


def get_best_score_candidate(
    db: Session,
    homework_id: int,
    student_id: int,
    *,
    latest_attempt_id: Optional[int] = None,
) -> Optional[HomeworkScoreCandidate]:
    """
    Best visible score for the submission summary: only the **latest attempt**'s
    candidates apply (if latest_attempt_id is set). On that attempt, any **teacher**
    score takes precedence over automatic scores so LLM output cannot override a
    teacher's grade in the UI.
    """
    query = (
        db.query(HomeworkScoreCandidate)
        .filter(
            HomeworkScoreCandidate.homework_id == homework_id,
            HomeworkScoreCandidate.student_id == student_id,
        )
    )
    if latest_attempt_id is not None:
        query = query.filter(HomeworkScoreCandidate.attempt_id == latest_attempt_id)
    candidates = query.all()
    valid_candidates = [
        c
        for c in candidates
        if c.score is not None and getattr(c.attempt, "counts_toward_final_score", True)
    ]
    if not valid_candidates:
        return None
    teacher_rows = [c for c in valid_candidates if c.source == "teacher"]
    if teacher_rows:
        return max(teacher_rows, key=_teacher_candidate_sort_key)
    auto_rows = [c for c in valid_candidates if c.source == "auto"]
    if auto_rows:
        return max(auto_rows, key=_auto_candidate_sort_key)
    return max(valid_candidates, key=_auto_candidate_sort_key)


def refresh_submission_summary(db: Session, summary: HomeworkSubmission) -> HomeworkSubmission:
    best_candidate = get_best_score_candidate(
        db, summary.homework_id, summary.student_id, latest_attempt_id=summary.latest_attempt_id
    )
    summary.review_score = best_candidate.score if best_candidate else None
    summary.review_comment = (best_candidate.comment or None) if best_candidate else None

    if summary.latest_attempt_id:
        latest_attempt = (
            db.query(HomeworkAttempt)
            .filter(HomeworkAttempt.id == summary.latest_attempt_id)
            .first()
        )
        if latest_attempt:
            summary.content = latest_attempt.content
            summary.attachment_name = latest_attempt.attachment_name
            summary.attachment_url = latest_attempt.attachment_url
            summary.submitted_at = latest_attempt.submitted_at
            latest_task = (
                db.query(HomeworkGradingTask)
                .filter(HomeworkGradingTask.attempt_id == latest_attempt.id)
                .order_by(HomeworkGradingTask.created_at.desc(), HomeworkGradingTask.id.desc())
                .first()
            )
            summary.latest_task_status = latest_task.status if latest_task else None
            summary.latest_task_error = latest_task.error_message if latest_task else None
    return summary


def ensure_course_llm_config(db: Session, subject_id: int, user_id: Optional[int] = None) -> CourseLLMConfig:
    config = db.query(CourseLLMConfig).filter(CourseLLMConfig.subject_id == subject_id).first()
    if config:
        return config
    config = CourseLLMConfig(subject_id=subject_id, created_by=user_id, updated_by=user_id)
    db.add(config)
    db.flush()
    return config


def build_task_summary(task: HomeworkGradingTask) -> str:
    status_map = {
        "queued": "排队中",
        "processing": "处理中",
        "success": "成功",
        "failed": "失败",
    }
    status_label = status_map.get(task.status, task.status)
    if task.error_message:
        return f"{status_label}: {task.error_message}"
    return status_label


def _reclaim_stale_processing_tasks(db: Session) -> int:
    stale_before = _now_utc() - timedelta(seconds=max(60, int(settings.LLM_GRADING_TASK_STALE_SECONDS or 600)))
    stale_tasks = (
        db.query(HomeworkGradingTask)
        .filter(
            HomeworkGradingTask.status == "processing",
            HomeworkGradingTask.updated_at.isnot(None),
            HomeworkGradingTask.updated_at < stale_before,
        )
        .all()
    )
    reclaimed = 0
    for task in stale_tasks:
        task.status = "queued"
        task.error_code = None
        task.error_message = None
        task.queue_reason = "reclaimed_stale_processing"
        task.task_summary = "已回收超时任务，等待重试"
        task.started_at = None
        task.finished_at = None
        task.updated_at = _now_utc()
        reclaimed += 1
    if reclaimed:
        db.commit()
    return reclaimed


def queue_grading_task(
    db: Session,
    attempt: HomeworkAttempt,
    queue_reason: str = "new_submission",
) -> HomeworkGradingTask:
    existing_task = (
        db.query(HomeworkGradingTask)
        .filter(
            HomeworkGradingTask.attempt_id == attempt.id,
            HomeworkGradingTask.status.in_(("queued", "processing")),
        )
        .order_by(HomeworkGradingTask.created_at.desc(), HomeworkGradingTask.id.desc())
        .first()
    )
    if existing_task:
        summary = (
            db.query(HomeworkSubmission)
            .filter(
                HomeworkSubmission.homework_id == attempt.homework_id,
                HomeworkSubmission.student_id == attempt.student_id,
            )
            .first()
        )
        if summary:
            summary.latest_task_status = existing_task.status
            summary.latest_task_error = existing_task.error_message
            refresh_submission_summary(db, summary)
        return existing_task

    task = HomeworkGradingTask(
        attempt_id=attempt.id,
        homework_id=attempt.homework_id,
        student_id=attempt.student_id,
        subject_id=attempt.subject_id,
        status="queued",
        queue_reason=queue_reason,
    )
    db.add(task)
    db.flush()
    summary = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == attempt.homework_id,
            HomeworkSubmission.student_id == attempt.student_id,
        )
        .first()
    )
    if summary:
        summary.latest_task_status = task.status
        summary.latest_task_error = None
        refresh_submission_summary(db, summary)
    return task


def validate_text_connectivity(
    base_url: str,
    api_key: str,
    model_name: str,
    connect_timeout_seconds: int,
    read_timeout_seconds: int,
) -> tuple[bool, str]:
    """OpenAI-style chat: text-only smoke test before multimodal check."""
    timeout = httpx.Timeout(connect=connect_timeout_seconds, read=read_timeout_seconds, write=read_timeout_seconds, pool=connect_timeout_seconds)
    messages = [
        {
            "role": "user",
            "content": "Please reply with the single word: OK",
        }
    ]
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 8,
    }
    endpoint_url = _build_chat_completion_url(base_url)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                endpoint_url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
    except httpx.HTTPError as exc:
        return False, f"纯文本连通性校验失败：{exc}"

    if response.status_code >= 400:
        return False, f"纯文本连通性校验失败：HTTP {response.status_code} {response.text[:300]}"

    try:
        data = response.json()
    except ValueError:
        return False, "纯文本连通性校验失败：返回内容不是 JSON。"

    content = _extract_message_content(data)
    if not content.strip():
        return False, "纯文本连通性校验失败：模型未返回可读文本。"

    return True, "纯文本请求校验通过。"


def validate_vision_connectivity(
    base_url: str,
    api_key: str,
    model_name: str,
    connect_timeout_seconds: int,
    read_timeout_seconds: int,
) -> tuple[bool, str]:
    timeout = httpx.Timeout(connect=connect_timeout_seconds, read=read_timeout_seconds, write=read_timeout_seconds, pool=connect_timeout_seconds)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Please reply with OK."},
                {"type": "image_url", "image_url": {"url": VISION_TEST_IMAGE_DATA_URL}},
            ],
        }
    ]
    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 5,
    }

    endpoint_url = _build_chat_completion_url(base_url)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                endpoint_url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            )
    except httpx.HTTPError as exc:
        return False, f"视觉能力校验失败：{exc}"

    if response.status_code >= 400:
        return False, f"视觉能力校验失败：HTTP {response.status_code} {response.text[:300]}"

    try:
        data = response.json()
    except ValueError:
        return False, "视觉能力校验失败：返回内容不是 JSON。"

    content = _extract_message_content(data)
    if not content.strip():
        return False, "视觉能力校验失败：模型未返回可读文本。"

    return True, "多模态（图像）输入校验通过。"


def validate_endpoint_connectivity(
    base_url: str,
    api_key: str,
    model_name: str,
    connect_timeout_seconds: int,
    read_timeout_seconds: int,
) -> tuple[bool, str]:
    ok, msg = validate_text_connectivity(
        base_url, api_key, model_name, connect_timeout_seconds, read_timeout_seconds
    )
    if not ok:
        return False, msg
    ok2, msg2 = validate_vision_connectivity(
        base_url, api_key, model_name, connect_timeout_seconds, read_timeout_seconds
    )
    if not ok2:
        return False, msg2
    return True, "端点连通性校验通过：已验证纯文本与多模态（图像）输入。"


def estimate_task_tokens(
    config: CourseLLMConfig,
    text_length: int,
    image_count: int,
) -> int:
    chars_per_token = config.estimated_chars_per_token or 4.0
    text_tokens = int(text_length / chars_per_token) + 200
    image_tokens = int(image_count * (config.estimated_image_tokens or 850))
    return text_tokens + image_tokens + int(config.max_output_tokens or 0)


def _get_usage_date(timezone_name: str) -> str:
    try:
        tz = ZoneInfo(timezone_name or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date().isoformat()


def _get_used_tokens_for_scope(
    db: Session,
    *,
    usage_date: str,
    timezone_name: str,
    student_id: Optional[int] = None,
    subject_id: Optional[int] = None,
) -> int:
    query = db.query(LLMTokenUsageLog).filter(
        LLMTokenUsageLog.usage_date == usage_date,
        LLMTokenUsageLog.timezone == timezone_name,
    )
    if student_id is not None:
        query = query.filter(LLMTokenUsageLog.student_id == student_id)
    if subject_id is not None:
        query = query.filter(LLMTokenUsageLog.subject_id == subject_id)
    total = 0
    for item in query.all():
        if item.total_tokens is not None:
            total += int(item.total_tokens)
        else:
            total += int(item.input_tokens or 0) + int(item.output_tokens or 0)
    return total


_quota_serialization_lock = threading.Lock()


def precheck_quota(
    db: Session,
    config: CourseLLMConfig,
    *,
    student_id: int,
    subject_id: Optional[int],
    estimated_tokens: int,
) -> tuple[bool, Optional[str]]:
    """Serialize read of usage vs limits to reduce double-spend under concurrent workers."""
    with _quota_serialization_lock:
        timezone_name = config.quota_timezone or "UTC"
        usage_date = _get_usage_date(timezone_name)
        if config.daily_student_token_limit:
            used_by_student = _get_used_tokens_for_scope(
                db,
                usage_date=usage_date,
                timezone_name=timezone_name,
                student_id=student_id,
            )
            if used_by_student + estimated_tokens > config.daily_student_token_limit:
                return False, "quota_exceeded"
        if config.daily_course_token_limit and subject_id:
            used_by_course = _get_used_tokens_for_scope(
                db,
                usage_date=usage_date,
                timezone_name=timezone_name,
                subject_id=subject_id,
            )
            if used_by_course + estimated_tokens > config.daily_course_token_limit:
                return False, "quota_exceeded"
        return True, None


def record_usage_if_needed(
    db: Session,
    task: HomeworkGradingTask,
    config: CourseLLMConfig,
    usage: dict[str, Any],
) -> None:
    existing = db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id == task.id).first()
    if existing:
        return
    with _quota_serialization_lock:
        timezone_name = config.quota_timezone or "UTC"
        usage_date = _get_usage_date(timezone_name)
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
        if total_tokens is None:
            total_tokens = int(prompt_tokens or 0) + int(completion_tokens or 0)
        if config.daily_student_token_limit:
            used_by_student = _get_used_tokens_for_scope(
                db,
                usage_date=usage_date,
                timezone_name=timezone_name,
                student_id=task.student_id,
            )
            if used_by_student + int(total_tokens or 0) > config.daily_student_token_limit:
                return
        if config.daily_course_token_limit and task.subject_id:
            used_by_course = _get_used_tokens_for_scope(
                db,
                usage_date=usage_date,
                timezone_name=timezone_name,
                subject_id=task.subject_id,
            )
            if used_by_course + int(total_tokens or 0) > config.daily_course_token_limit:
                return

        db.add(
            LLMTokenUsageLog(
                task_id=task.id,
                subject_id=task.subject_id,
                student_id=task.student_id,
                usage_date=usage_date,
                timezone=timezone_name,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=total_tokens,
            )
        )
        task.billed_input_tokens = prompt_tokens
        task.billed_output_tokens = completion_tokens
        task.billed_total_tokens = total_tokens


def process_next_grading_task() -> bool:
    db = SessionLocal()
    try:
        _reclaim_stale_processing_tasks(db)
        task = (
            db.query(HomeworkGradingTask)
            .filter(HomeworkGradingTask.status == "queued")
            .order_by(HomeworkGradingTask.created_at.asc(), HomeworkGradingTask.id.asc())
            .first()
        )
        if not task:
            return False
        updated = (
            db.query(HomeworkGradingTask)
            .filter(
                HomeworkGradingTask.id == task.id,
                HomeworkGradingTask.status == "queued",
            )
            .update(
                {
                    HomeworkGradingTask.status: "processing",
                    HomeworkGradingTask.started_at: _now_utc(),
                    HomeworkGradingTask.updated_at: _now_utc(),
                    HomeworkGradingTask.task_summary: "处理中",
                },
                synchronize_session=False,
            )
        )
        if not updated:
            db.rollback()
            return False
        db.commit()
        process_grading_task(task.id)
        return True
    finally:
        db.close()


def process_grading_task(task_id: int) -> None:
    with _grading_lock_for_task(task_id):
        _process_grading_task_unlocked(task_id)


def _process_grading_task_unlocked(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == task_id).first()
        if not task:
            return
        if task.status in ("success", "failed"):
            return
        if task.status == "queued":
            # Claim the task (tests call process_grading_task directly; worker uses process_next which pre-sets processing).
            now = _now_utc()
            n = (
                db.query(HomeworkGradingTask)
                .filter(HomeworkGradingTask.id == task_id, HomeworkGradingTask.status == "queued")
                .update(
                    {
                        HomeworkGradingTask.status: "processing",
                        HomeworkGradingTask.started_at: now,
                        HomeworkGradingTask.updated_at: now,
                        HomeworkGradingTask.task_summary: "处理中",
                    },
                    synchronize_session=False,
                )
            )
            if not n:
                return
            db.commit()
            task = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == task_id).first()
        elif task.status != "processing":
            return
        try:
            _run_grading_after_claim(db, task_id, task)
        except Exception as exc:
            db.rollback()
            task2 = db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id == task_id).first()
            if task2:
                _mark_task_failed(db, task2, "unexpected_error", f"评分任务异常：{exc}")
    finally:
        db.close()


def _run_grading_after_claim(db: Session, task_id: int, task: HomeworkGradingTask) -> None:
    attempt = db.query(HomeworkAttempt).filter(HomeworkAttempt.id == task.attempt_id).first()
    if not attempt:
        _mark_task_failed(db, task, "attempt_not_found", "找不到对应的提交记录。")
        return
    homework = db.query(Homework).filter(Homework.id == task.homework_id).first()
    if not homework:
        _mark_task_failed(db, task, "homework_not_found", "找不到对应的作业。")
        return
    if not homework.auto_grading_enabled:
        _mark_task_failed(db, task, "auto_grading_disabled", "当前作业未启用自动评分。")
        return
    if not task.subject_id:
        _mark_task_failed(db, task, "course_missing", "当前作业未关联课程，无法使用课程级 LLM 配置。")
        return

    config = (
        db.query(CourseLLMConfig)
        .options(
            joinedload(CourseLLMConfig.groups)
            .joinedload(LLMGroup.members)
            .joinedload(CourseLLMConfigEndpoint.preset),
            joinedload(CourseLLMConfig.endpoints).joinedload(CourseLLMConfigEndpoint.preset),
        )
        .filter(CourseLLMConfig.subject_id == task.subject_id)
        .first()
    )
    if not config or not config.is_enabled:
        _mark_task_failed(db, task, "llm_config_disabled", "当前课程未启用 LLM 配置。")
        return

    if not (config.groups or []) and not (config.endpoints or []):
        _mark_task_failed(db, task, "endpoint_missing", "当前课程未配置可用端点。")
        return

    material = _build_student_material(homework, attempt, config)
    base_manifest = material["artifact_manifest"] or {}
    if not isinstance(base_manifest, dict):
        base_manifest = {}
    task.artifact_manifest = {**base_manifest, "llm_routing": {"version": 1, "status": "pending"}}
    task.input_token_estimate = material["estimated_tokens"]
    task.task_summary = material["summary"]

    if material["all_empty"]:
        _mark_task_failed(db, task, "no_usable_content", "附件处理后没有可评分内容。")
        return

    allowed, error_code = precheck_quota(
        db,
        config,
        student_id=task.student_id,
        subject_id=task.subject_id,
        estimated_tokens=material["estimated_tokens"],
    )
    if not allowed:
        _mark_task_failed(db, task, error_code or "quota_exceeded", "今日额度已用尽，自动评分未执行。")
        return

    teacher_exists = (
        db.query(HomeworkScoreCandidate)
        .filter(
            HomeworkScoreCandidate.attempt_id == attempt.id,
            HomeworkScoreCandidate.source == "teacher",
        )
        .first()
    )
    if teacher_exists:
        task.status = "success"
        task.error_code = None
        task.error_message = None
        task.finished_at = _now_utc()
        task.task_summary = "已跳过：该次提交已有教师评分，未调用模型。"
        summary = (
            db.query(HomeworkSubmission)
            .filter(
                HomeworkSubmission.homework_id == attempt.homework_id,
                HomeworkSubmission.student_id == attempt.student_id,
            )
            .first()
        )
        if summary:
            summary.latest_task_status = task.status
            summary.latest_task_error = None
            refresh_submission_summary(db, summary)
        db.commit()
        return

    response = _grade_with_endpoint_group(
        task=task,
        homework=homework,
        attempt=attempt,
        config=config,
        material=material,
    )

    candidate = HomeworkScoreCandidate(
        attempt_id=attempt.id,
        homework_id=homework.id,
        student_id=attempt.student_id,
        source="auto",
        score=normalize_score_for_homework(homework, response["score"]),
        comment=response["comment"],
        source_metadata={
            "task_id": task.id,
            "endpoint_id": response["endpoint_id"],
            "raw_response_excerpt": response["raw_response"][:1000],
        },
    )
    db.add(candidate)
    db.flush()

    task.status = "success"
    task.error_code = None
    task.error_message = None
    task.finished_at = _now_utc()
    task.task_summary = "评分成功"
    record_usage_if_needed(db, task, config, response["usage"])

    summary = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == attempt.homework_id,
            HomeworkSubmission.student_id == attempt.student_id,
        )
        .first()
    )
    if summary:
        summary.latest_task_status = task.status
        summary.latest_task_error = None
        refresh_submission_summary(db, summary)

    db.commit()


def _mark_task_failed(
    db: Session,
    task: HomeworkGradingTask,
    error_code: str,
    error_message: str,
) -> None:
    task.status = "failed"
    task.error_code = error_code
    task.error_message = error_message
    task.finished_at = _now_utc()
    task.task_summary = error_message
    summary = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == task.homework_id,
            HomeworkSubmission.student_id == task.student_id,
        )
        .first()
    )
    if summary:
        summary.latest_task_status = task.status
        summary.latest_task_error = error_message
        refresh_submission_summary(db, summary)
    db.commit()


def _collect_grading_endpoints_for_config(
    config: CourseLLMConfig,
) -> tuple[list[LLMGroup], list[CourseLLMConfigEndpoint]]:
    """Return (ordered groups, flat legacy endpoints when no groups are defined)."""
    groups = sorted(
        [g for g in (config.groups or []) if g is not None],
        key=lambda x: (x.priority, x.id),
    )
    if groups and any((g.members or []) for g in groups):
        return groups, []
    flat = sorted(
        (config.endpoints or []),
        key=lambda row: (row.priority, row.id),
    )
    return [], flat


def _grade_with_endpoint_group(
    *,
    task: HomeworkGradingTask,
    homework: Homework,
    attempt: HomeworkAttempt,
    config: CourseLLMConfig,
    material: dict[str, Any],
) -> dict[str, Any]:
    group_rows, flat_endpoints = _collect_grading_endpoints_for_config(config)
    if group_rows:
        routing = GroupRoutingContext.from_config(group_rows, task_id=task.id)

        def _update_routing_artifact(merge: dict[str, Any]) -> None:
            if not isinstance(task.artifact_manifest, dict):
                return
            base = dict(routing.routing_payload())
            base.update(merge)
            task.artifact_manifest["llm_routing"] = base

        _update_routing_artifact({"status": "routing"})

        last_error: Optional[str] = None
        global_index = 0
        for group_state in routing.group_states:
            group_state.apply_round_robin_start(task.id)
            while group_state.current_order:
                link = group_state.current_order[0]
                global_index += 1
                preset: LLMEndpointPreset = link.preset
                if not preset or not preset.is_active or preset.validation_status != "validated" or not preset.supports_vision:
                    last_error = f"端点 {getattr(preset, 'name', global_index)} 不可用或未通过视觉校验。"
                    group_state.remove_member(link)
                    _update_routing_artifact(
                        {
                            "status": "invalid_member_skipped",
                            "last_error": last_error,
                        }
                    )
                    continue
                task.current_endpoint_index = global_index
                attempt_limit = max(1, int(preset.max_retries or 0) + 1)
                member_done = False
                for request_attempt in range(1, attempt_limit + 1):
                    task.current_attempt = request_attempt
                    try:
                        score_result = _request_grade_from_endpoint(
                            preset=preset,
                            homework=homework,
                            attempt=attempt,
                            config=config,
                            material=material,
                        )
                        score_result["endpoint_id"] = preset.id
                        _update_routing_artifact({"status": "ok"})
                        return score_result
                    except RetryableLLMError as exc:
                        last_error = str(exc)
                        n_before = len(group_state.current_order)
                        routing.note_failure(group_state, link, exc)
                        if request_attempt >= attempt_limit:
                            if n_before == 1:
                                group_state.remove_member(link)
                            _update_routing_artifact(
                                {
                                    "status": "adaptive_shift",
                                    "last_error": last_error,
                                }
                            )
                            member_done = True
                            break
                        _update_routing_artifact(
                            {
                                "status": "retry_backoff",
                                "last_error": last_error,
                            }
                        )
                        wait_seconds = min(
                            int(preset.initial_backoff_seconds or 2) * (2 ** (request_attempt - 1)),
                            120,
                        )
                        if os.environ.get("LLM_GRADING_TEST_SKIP_BACKOFF") != "1":
                            time.sleep(wait_seconds)
                    except NonRetryableLLMError as exc:
                        last_error = str(exc)
                        routing.note_failure(group_state, link, exc)
                        _update_routing_artifact({"status": "endpoint_error", "last_error": last_error})
                        group_state.remove_member(link)
                        member_done = True
                        break
        _update_routing_artifact({"status": "failed", "message": last_error or ""})
        raise NonRetryableLLMError(last_error or "所有组内端点都调用失败。")

    last_error_flat: Optional[str] = None
    for endpoint_index, link in enumerate(flat_endpoints, start=1):
        preset: LLMEndpointPreset = link.preset
        if not preset or not preset.is_active or preset.validation_status != "validated" or not preset.supports_vision:
            last_error_flat = f"端点 {getattr(preset, 'name', endpoint_index)} 不可用或未通过视觉校验。"
            continue
        task.current_endpoint_index = endpoint_index
        attempt_limit = max(1, int(preset.max_retries or 0) + 1)
        for request_attempt in range(1, attempt_limit + 1):
            task.current_attempt = request_attempt
            try:
                score_result = _request_grade_from_endpoint(
                    preset=preset,
                    homework=homework,
                    attempt=attempt,
                    config=config,
                    material=material,
                )
                score_result["endpoint_id"] = preset.id
                if isinstance(task.artifact_manifest, dict) and "llm_routing" in (task.artifact_manifest or {}):
                    task.artifact_manifest["llm_routing"] = (task.artifact_manifest.get("llm_routing") or {}) | {
                        "version": 1,
                        "mode": "legacy_priority",
                        "status": "ok",
                    }
                return score_result
            except RetryableLLMError as exc:
                last_error_flat = str(exc)
                if request_attempt >= attempt_limit:
                    break
                wait_seconds = min(
                    int(preset.initial_backoff_seconds or 2) * (2 ** (request_attempt - 1)),
                    120,
                )
                if os.environ.get("LLM_GRADING_TEST_SKIP_BACKOFF") != "1":
                    time.sleep(wait_seconds)
            except NonRetryableLLMError as exc:
                last_error_flat = str(exc)
                break
    if isinstance(task.artifact_manifest, dict) and "llm_routing" in (task.artifact_manifest or {}):
        task.artifact_manifest["llm_routing"] = (task.artifact_manifest.get("llm_routing") or {}) | {
            "version": 1,
            "mode": "legacy_priority",
            "status": "failed",
        }
    raise NonRetryableLLMError(last_error_flat or "所有端点都调用失败。")


def _build_chat_completion_url(base_url: str) -> str:
    normalized = base_url.rstrip("/") + "/"
    if normalized.endswith("/chat/completions/"):
        return normalized[:-1]
    return urljoin(normalized, "chat/completions")


def _request_grade_from_endpoint(
    *,
    preset: LLMEndpointPreset,
    homework: Homework,
    attempt: HomeworkAttempt,
    config: CourseLLMConfig,
    material: dict[str, Any],
) -> dict[str, Any]:
    timeout = httpx.Timeout(
        connect=preset.connect_timeout_seconds or 10,
        read=preset.read_timeout_seconds or 120,
        write=preset.read_timeout_seconds or 120,
        pool=preset.connect_timeout_seconds or 10,
    )
    payload = {
        "model": preset.model_name,
        "messages": _build_scoring_messages(homework, attempt, config, material),
        "temperature": 0.2,
        "max_tokens": config.max_output_tokens or 1200,
    }
    endpoint_url = _build_chat_completion_url(preset.base_url)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                endpoint_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {preset.api_key}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.TimeoutException as exc:
        raise RetryableLLMError(f"请求超时：{exc}") from exc
    except httpx.HTTPError as exc:
        raise RetryableLLMError(f"网络请求失败：{exc}") from exc

    if response.status_code in NON_RETRYABLE_STATUS_CODES:
        raise NonRetryableLLMError(f"鉴权或权限失败：HTTP {response.status_code}")
    if response.status_code == 413:
        raise NonRetryableLLMError("请求内容过大，端点拒绝处理。")
    if response.status_code in RETRYABLE_STATUS_CODES:
        raise RetryableLLMError(f"端点暂时不可用：HTTP {response.status_code}")
    if response.status_code >= 400:
        raise NonRetryableLLMError(f"端点请求失败：HTTP {response.status_code} {response.text[:300]}")

    try:
        data = response.json()
    except ValueError as exc:
        raise RetryableLLMError("模型返回的不是合法 JSON 响应。") from exc

    raw_content = _extract_message_content(data)
    score_payload = _parse_scoring_json(raw_content, homework)
    usage = data.get("usage") or {}
    return {
        "score": score_payload["score"],
        "comment": score_payload["comment"],
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
        "raw_response": raw_content,
    }


def _extract_message_content(response_json: dict[str, Any]) -> str:
    choices = response_json.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text") or "")
        return "\n".join(part for part in parts if part)
    return ""


def _strip_markdown_fence(text: str) -> str:
    match = JSON_FENCE_PATTERN.match(text or "")
    if match:
        return match.group(1).strip()
    return (text or "").strip()


def _extract_first_json_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _parse_scoring_json(raw_text: str, homework: Homework) -> dict[str, Any]:
    text = _strip_markdown_fence(raw_text)
    payload_text = text
    try:
        payload = json.loads(payload_text)
    except ValueError:
        payload_text = _extract_first_json_object(text or "") or ""
        if not payload_text:
            raise RetryableLLMError("模型未按要求输出 JSON 对象。")
        try:
            payload = json.loads(payload_text)
        except ValueError as exc:
            raise RetryableLLMError("模型输出 JSON 解析失败。") from exc
    if not isinstance(payload, dict):
        raise RetryableLLMError("模型输出的根节点不是对象。")
    if "score" not in payload or "comment" not in payload:
        raise RetryableLLMError("模型输出缺少 score/comment 字段。")
    try:
        score = float(payload["score"])
    except (TypeError, ValueError) as exc:
        raise RetryableLLMError("模型输出的 score 不是有效数字。") from exc
    if score < 0 or score > float(homework.max_score or 100):
        raise RetryableLLMError("模型输出分数超出允许范围。")
    comment = payload.get("comment")
    if comment is None:
        comment = ""
    if not isinstance(comment, str):
        comment = str(comment)
    return {"score": score, "comment": comment}


def _build_scoring_messages(
    homework: Homework,
    attempt: HomeworkAttempt,
    config: CourseLLMConfig,
    material: dict[str, Any],
) -> list[dict[str, Any]]:
    system_prompt = config.system_prompt or (
        "你是一个严格遵守格式要求的课程作业评分助手。"
        "你必须只输出 JSON 对象，且字段固定为 score 与 comment。"
        "绝不能在 JSON 前后输出任何额外说明。"
    )
    response_language = homework.response_language or config.response_language or "zh-CN"
    teacher_prompt = config.teacher_prompt or ""
    assignment_text = "\n\n".join(material["assignment_texts"])
    student_intro = (
        f"作业标题：{homework.title}\n"
        f"满分：{normalize_score_for_homework(homework, homework.max_score)}\n"
        f"评分精度：{'1 位小数' if homework.grade_precision == 'decimal_1' else '整数'}\n"
        f"响应语言：{response_language}\n"
        f"提交是否迟交：{'是' if attempt.is_late else '否'}\n"
        f"迟交默认是否影响得分：{'是' if homework.late_submission_affects_score else '否'}\n"
    )
    user_parts: list[dict[str, Any]] = [{"type": "text", "text": assignment_text + "\n\n" + teacher_prompt + "\n\n" + student_intro}]
    for block in material["student_blocks"]:
        if block.block_type == "text":
            user_parts.append({"type": "text", "text": block.text or ""})
        elif block.block_type == "image":
            user_parts.append({"type": "image_url", "image_url": {"url": block.image_data_url}})
    if material["notes_text"]:
        user_parts.append({"type": "text", "text": material["notes_text"]})
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_parts},
    ]


def _truncate_text(value: str, limit: int = MAX_FILE_TEXT_CHARS) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    return value[:limit], True


def _decode_bytes_as_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _safe_relative_path(path_text: str) -> Optional[str]:
    normalized = PurePosixPath(path_text.replace("\\", "/"))
    safe_parts = []
    for part in normalized.parts:
        if part in {"", ".", ".."}:
            continue
        safe_parts.append(part)
    if not safe_parts:
        return None
    return "/".join(safe_parts)


def _guess_mime_type(path: str) -> str:
    mime_type, _ = mimetypes.guess_type(path)
    return mime_type or "application/octet-stream"


def _bytes_to_data_url(path: str, content: bytes) -> str:
    mime_type = _guess_mime_type(path)
    return f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"


def _extract_docx_text(content: bytes) -> str:
    document = Document(io.BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs)


def _extract_pdf_images(content: bytes, path: str) -> list[MaterialBlock]:
    blocks: list[MaterialBlock] = []
    document = fitz.open(stream=content, filetype="pdf")
    try:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image_bytes = pixmap.tobytes("png")
            blocks.append(
                MaterialBlock(
                    priority=3,
                    path=f"{path}#page-{index}",
                    block_type="image",
                    image_data_url=f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}",
                    estimated_tokens=settings.DEFAULT_ESTIMATED_IMAGE_TOKENS,
                )
            )
    finally:
        document.close()
    return blocks


def _extract_ipynb_blocks(content: bytes, path: str) -> list[MaterialBlock]:
    try:
        notebook = json.loads(content.decode("utf-8"))
    except Exception:
        return []

    blocks: list[MaterialBlock] = []
    text_fragments: list[str] = []
    for index, cell in enumerate(notebook.get("cells") or [], start=1):
        cell_type = cell.get("cell_type") or "cell"
        source = "".join(cell.get("source") or [])
        if source.strip():
            text_fragments.append(f"## Cell {index} ({cell_type})\n{source.strip()}")
        for output in cell.get("outputs") or []:
            if output.get("output_type") == "stream":
                text = "".join(output.get("text") or [])
                if text.strip():
                    text_fragments.append(f"Output:\n{text.strip()[:MAX_IPYNB_OUTPUT_CHARS]}")
            data = output.get("data") or {}
            text_plain = data.get("text/plain")
            if text_plain:
                text = "".join(text_plain if isinstance(text_plain, list) else [str(text_plain)])
                if text.strip():
                    text_fragments.append(f"Output:\n{text.strip()[:MAX_IPYNB_OUTPUT_CHARS]}")
            image_png = data.get("image/png")
            if image_png:
                if isinstance(image_png, list):
                    image_png = "".join(image_png)
                blocks.append(
                    MaterialBlock(
                        priority=3,
                        path=f"{path}#cell-{index}-output",
                        block_type="image",
                        image_data_url=f"data:image/png;base64,{image_png}",
                        estimated_tokens=settings.DEFAULT_ESTIMATED_IMAGE_TOKENS,
                    )
                )
    if text_fragments:
        text, truncated = _truncate_text("\n\n".join(text_fragments))
        suffix = "\n\n[说明] Ipynb 文本输出已截断。" if truncated else ""
        blocks.insert(
            0,
            MaterialBlock(
                priority=2,
                path=path,
                block_type="text",
                text=f"### {path}\n{text}{suffix}",
                estimated_tokens=int(len(text) / 4) + 50,
            ),
        )
    return blocks


def _classify_and_extract(path: str, content: bytes) -> list[MaterialBlock]:
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return _extract_pdf_images(content, path)
    if suffix in IPYNB_EXTENSIONS:
        return _extract_ipynb_blocks(content, path)
    if suffix in SUPPORTED_IMAGE_EXTENSIONS:
        return [
            MaterialBlock(
                priority=3,
                path=path,
                block_type="image",
                image_data_url=_bytes_to_data_url(path, content),
                estimated_tokens=settings.DEFAULT_ESTIMATED_IMAGE_TOKENS,
            )
        ]
    if suffix == ".docx":
        text = _extract_docx_text(content)
    elif suffix in SUPPORTED_TEXT_EXTENSIONS:
        text = _decode_bytes_as_text(content)
    else:
        return []
    text = text.strip()
    if not text:
        return []
    text, truncated = _truncate_text(text)
    suffix_note = "\n\n[说明] 文件内容过长，已截断。" if truncated else ""
    return [
        MaterialBlock(
            priority=2,
            path=path,
            block_type="text",
            text=f"### {path}\n{text}{suffix_note}",
            estimated_tokens=int(len(text) / 4) + 50,
        )
    ]


def _walk_zip_bytes(
    content: bytes,
    *,
    root_path: str,
    depth: int,
    state: dict[str, Any],
) -> list[MaterialBlock]:
    blocks: list[MaterialBlock] = []
    if depth > MAX_ZIP_DEPTH:
        state["skipped"].append({"path": root_path, "reason": "超过最大嵌套深度"})
        return blocks
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = sorted(archive.infolist(), key=lambda item: (item.filename or "").lower())
            for info in infos:
                if info.is_dir():
                    continue
                safe_child_path = _safe_relative_path(info.filename or "")
                if not safe_child_path:
                    state["skipped"].append({"path": f"{root_path}/{info.filename}", "reason": "非法路径"})
                    continue
                state["file_count"] += 1
                state["total_bytes"] += max(0, int(info.file_size or 0))
                if state["file_count"] > MAX_ZIP_FILES or state["total_bytes"] > MAX_ZIP_TOTAL_BYTES:
                    state["skipped"].append({"path": f"{root_path}/{safe_child_path}", "reason": "超出展开文件数或总大小限制"})
                    continue
                child_bytes = archive.read(info)
                child_path = f"{root_path}/{safe_child_path}"
                child_suffix = PurePosixPath(safe_child_path).suffix.lower()
                if child_suffix in ZIP_EXTENSIONS:
                    blocks.extend(_walk_zip_bytes(child_bytes, root_path=child_path, depth=depth + 1, state=state))
                else:
                    child_blocks = _classify_and_extract(child_path, child_bytes)
                    if child_blocks:
                        blocks.extend(child_blocks)
                    else:
                        state["skipped"].append({"path": child_path, "reason": "无法识别或提取为空"})
    except zipfile.BadZipFile:
        state["skipped"].append({"path": root_path, "reason": "压缩包损坏或格式不合法"})
    return blocks


def _collect_attachment_blocks(summary_path: str, attachment_name: str) -> tuple[list[MaterialBlock], list[dict[str, str]]]:
    file_path = get_attachment_file_path(summary_path)
    if not file_path or not file_path.exists():
        return [], [{"path": attachment_name or "attachment", "reason": "找不到原始附件文件"}]
    content = file_path.read_bytes()
    suffix = file_path.suffix.lower()
    state = {"file_count": 0, "total_bytes": 0, "skipped": []}
    if suffix in ZIP_EXTENSIONS or (attachment_name or "").lower().endswith(".zip"):
        blocks = _walk_zip_bytes(content, root_path=attachment_name or file_path.name, depth=1, state=state)
        return blocks, state["skipped"]
    blocks = _classify_and_extract(attachment_name or file_path.name, content)
    if blocks:
        return blocks, []
    return [], [{"path": attachment_name or file_path.name, "reason": "无法识别或提取为空"}]


def _build_student_material(
    homework: Homework,
    attempt: HomeworkAttempt,
    config: CourseLLMConfig,
) -> dict[str, Any]:
    assignment_texts = [
        f"作业标题：{homework.title}",
        f"作业要求：\n{homework.content or '无'}",
    ]
    if homework.reference_answer:
        assignment_texts.append(f"参考答案或提示：\n{homework.reference_answer}")
    if homework.rubric_text:
        assignment_texts.append(f"评分要点：\n{homework.rubric_text}")

    student_blocks: list[MaterialBlock] = []
    skipped: list[dict[str, str]] = []
    if attempt.content:
        text, truncated = _truncate_text(attempt.content)
        note = "\n\n[说明] 提交说明过长，已截断。" if truncated else ""
        student_blocks.append(
            MaterialBlock(
                priority=2,
                path="submission-note",
                block_type="text",
                text=f"### 提交说明\n{text}{note}",
                estimated_tokens=int(len(text) / 4) + 50,
            )
        )
    if attempt.attachment_url:
        attachment_blocks, skipped_items = _collect_attachment_blocks(
            attempt.attachment_url,
            attempt.attachment_name or "attachment",
        )
        student_blocks.extend(attachment_blocks)
        skipped.extend(skipped_items)

    student_blocks.sort(key=lambda item: (item.priority, item.path))
    text_budget = int((config.max_input_tokens or 16000) * (config.estimated_chars_per_token or 4.0))
    reserved_text = "\n\n".join(assignment_texts)
    remaining_chars = max(2000, text_budget - len(reserved_text))
    remaining_image_budget = config.max_input_tokens or 16000
    final_blocks: list[MaterialBlock] = []
    truncation_notes: list[str] = []
    for block in student_blocks:
        if block.block_type == "text":
            block_text = block.text or ""
            if remaining_chars <= 0:
                skipped.append({"path": block.path, "reason": "超出输入长度预算"})
                continue
            if len(block_text) > remaining_chars:
                truncated_text, _ = _truncate_text(block_text, remaining_chars)
                final_blocks.append(
                    MaterialBlock(
                        priority=block.priority,
                        path=block.path,
                        block_type="text",
                        text=truncated_text,
                        estimated_tokens=int(len(truncated_text) / 4) + 50,
                    )
                )
                truncation_notes.append(f"{block.path} 已按预算截断")
                remaining_chars = 0
                continue
            final_blocks.append(block)
            remaining_chars -= len(block_text)
        else:
            estimated_tokens = block.estimated_tokens or settings.DEFAULT_ESTIMATED_IMAGE_TOKENS
            if remaining_image_budget < estimated_tokens:
                skipped.append({"path": block.path, "reason": "超出图片 token 预算"})
                continue
            final_blocks.append(block)
            remaining_image_budget -= estimated_tokens

    notes_text_parts: list[str] = []
    if truncation_notes:
        notes_text_parts.append("截断说明：\n- " + "\n- ".join(truncation_notes))
    if skipped:
        skipped_lines = [f"{item['path']}：{item['reason']}" for item in skipped]
        notes_text_parts.append("未纳入内容：\n- " + "\n- ".join(skipped_lines))
    notes_text = "\n\n".join(notes_text_parts)
    estimated_tokens = estimate_task_tokens(
        config,
        text_length=len(reserved_text) + sum(len(block.text or "") for block in final_blocks if block.block_type == "text") + len(notes_text),
        image_count=len([block for block in final_blocks if block.block_type == "image"]),
    )
    artifact_manifest = {
        "included": [
            {"path": block.path, "type": block.block_type}
            for block in final_blocks
        ],
        "skipped": skipped,
    }
    return {
        "assignment_texts": assignment_texts,
        "student_blocks": final_blocks,
        "notes_text": notes_text,
        "estimated_tokens": estimated_tokens,
        "artifact_manifest": artifact_manifest,
        "summary": f"纳入 {len(final_blocks)} 个片段，跳过 {len(skipped)} 个文件/片段",
        "all_empty": len(final_blocks) == 0,
    }
