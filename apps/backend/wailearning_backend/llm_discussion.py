"""Synchronous LLM replies for course discussions (same endpoint routing + quota as grading)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.db.database import SessionLocal
from apps.backend.wailearning_backend.llm_grading import (
    GroupRoutingContext,
    _collect_grading_endpoints_for_config,
    _preset_eligible_for_grading,
    ensure_course_llm_config,
)
from apps.backend.wailearning_backend.domains.llm.errors import NonRetryableLLMError, RetryableLLMError
from apps.backend.wailearning_backend.domains.llm.protocol import (
    NON_RETRYABLE_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    build_chat_completion_url as _build_chat_completion_url,
)
from apps.backend.wailearning_backend.domains.llm.discussion_ui import strip_llm_ui_prefix
from apps.backend.wailearning_backend.domains.llm.quota import (
    record_discussion_usage_if_needed,
    release_discussion_quota_reservation,
    reserve_discussion_quota_tokens,
)
from apps.backend.wailearning_backend.db.models import (
    CourseDiscussionEntry,
    CourseLLMConfig,
    CourseMaterial,
    DiscussionLLMJob,
    Homework,
    HomeworkAttempt,
    HomeworkSubmission,
    LLMEndpointPreset,
    Student,
    Subject,
    User,
)

def resolve_student_for_discussion_llm(db: Session, user: User, course: Subject) -> Student:
    """Student roster row for quota billing (username == student_no, same class as course)."""
    cid = course.class_id
    if cid is None:
        raise ValueError("course has no class")
    row = (
        db.query(Student)
        .filter(Student.student_no == user.username, Student.class_id == int(cid))
        .order_by(Student.id.asc())
        .first()
    )
    if not row:
        raise ValueError("no_linked_student")
    return row


def _strip_for_context(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 20] + "\n…（已截断）"


def _homework_context_blocks(db: Session, hw: Homework, *, student_id: int) -> list[str]:
    parts: list[str] = []
    parts.append(f"【作业标题】\n{hw.title}")
    parts.append(f"【作业说明】\n{_strip_for_context(hw.content or '', 12000)}")
    if (hw.rubric_text or "").strip():
        parts.append(f"【评分要点】\n{_strip_for_context(hw.rubric_text, 8000)}")
    if (hw.reference_answer or "").strip():
        parts.append(f"【参考答案】\n{_strip_for_context(hw.reference_answer, 8000)}")
    sub = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.homework_id == hw.id, HomeworkSubmission.student_id == student_id)
        .first()
    )
    if sub:
        attempt = None
        if sub.latest_attempt_id:
            attempt = db.query(HomeworkAttempt).filter(HomeworkAttempt.id == sub.latest_attempt_id).first()
        if not attempt:
            attempt = (
                db.query(HomeworkAttempt)
                .filter(HomeworkAttempt.homework_id == hw.id, HomeworkAttempt.student_id == student_id)
                .order_by(HomeworkAttempt.submitted_at.desc(), HomeworkAttempt.id.desc())
                .first()
            )
        if attempt:
            parts.append(
                "【该生本人最近一次提交概要】\n"
                f"说明/正文：\n{_strip_for_context(attempt.content or '', 8000)}\n"
                f"附件：{(attempt.attachment_name or '无').strip()}"
            )
        else:
            parts.append("【该生本人提交】暂无提交记录。")
    else:
        parts.append("【该生本人提交】暂无提交记录。")
    return parts


def _material_context_blocks(mat: CourseMaterial) -> list[str]:
    return [
        f"【资料标题】\n{mat.title}",
        f"【资料正文】\n{_strip_for_context(mat.content or '', 16000)}",
        f"附件：{(mat.attachment_name or '无').strip()}",
    ]


def _discussion_thread_text(
    db: Session,
    *,
    target_type: str,
    target_id: int,
    subject_id: int,
    class_id: int,
    max_messages: int = 200,
) -> str:
    rows = (
        db.query(CourseDiscussionEntry, User)
        .join(User, User.id == CourseDiscussionEntry.author_user_id)
        .filter(
            CourseDiscussionEntry.target_type == target_type,
            CourseDiscussionEntry.target_id == target_id,
            CourseDiscussionEntry.subject_id == subject_id,
            CourseDiscussionEntry.class_id == class_id,
        )
        .order_by(CourseDiscussionEntry.created_at.asc(), CourseDiscussionEntry.id.asc())
        .limit(max_messages)
        .all()
    )
    lines: list[str] = []
    for entry, author in rows:
        who = author.real_name or author.username
        kind = "（智能助教）" if entry.message_kind == "llm_assistant" else ""
        inv = " [调用LLM]" if entry.llm_invocation else ""
        lines.append(f"- {who}{kind}{inv}: {entry.body}")
    return "\n".join(lines) if lines else "（尚无留言）"


def _estimate_discussion_prompt_tokens(messages: list[dict[str, Any]], max_output_tokens: int) -> int:
    """Rough prompt size + configured max output for reservation."""
    enc = __import__("tiktoken").get_encoding("o200k_base")
    n = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            n += len(enc.encode(c))
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") == "text":
                    n += len(enc.encode(part.get("text") or ""))
    return int(n + max(256, int(max_output_tokens or 0)))


def _build_discussion_messages(
    *,
    context_text: str,
    thread_text: str,
    user_message: str,
    response_language: Optional[str],
) -> list[dict[str, Any]]:
    lang = (response_language or "zh").strip()
    system = (
        "你是智能教学辅助系统中的「智能助教」，仅根据下方提供的课程材料、作业说明与讨论区公开留言作答。\n"
        "规则：\n"
        "1) 只使用给定上下文；若信息不足请明确说明，不要编造。\n"
        "2) 讨论区为公开实名讨论；回答应专业、友善、面向学习辅导。\n"
        "3) 若上下文含「该生本人提交」，那是当前提问学生自己的作业，可引用；不要臆测其他同学提交。\n"
        f"4) 主要使用语言：{lang}。\n"
        "5) 直接给出助教回复正文，不要使用 JSON 或代码围栏包裹全篇。"
    )
    user_block = (
        "【课程/条目上下文】\n"
        f"{context_text}\n\n"
        "【讨论区留言（按时间顺序）】\n"
        f"{thread_text}\n\n"
        "【当前学生的新留言】\n"
        f"{user_message}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user_block},
    ]


def _request_discussion_completion(
    *,
    preset: LLMEndpointPreset,
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    job: DiscussionLLMJob,
) -> dict[str, Any]:
    timeout = httpx.Timeout(
        connect=preset.connect_timeout_seconds or 10,
        read=preset.read_timeout_seconds or 120,
        write=preset.read_timeout_seconds or 120,
        pool=preset.connect_timeout_seconds or 10,
    )
    payload = {
        "model": preset.model_name,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": int(max_output_tokens),
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

    choices = data.get("choices") or []
    raw = ""
    if choices:
        msg = (choices[0] or {}).get("message") or {}
        raw = msg.get("content") or ""
    if not str(raw).strip():
        raise RetryableLLMError("模型返回空内容。")
    usage = data.get("usage") or {}
    return {
        "text": str(raw).strip(),
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        },
    }


def _call_discussion_with_routing(
    *,
    db: Session,
    config: CourseLLMConfig,
    messages: list[dict[str, Any]],
    max_output_tokens: int,
    job: DiscussionLLMJob,
) -> dict[str, Any]:
    """Reuse group + flat endpoint routing like grading (text-only; vision not required)."""
    group_rows, flat_endpoints = _collect_grading_endpoints_for_config(config)
    need_vision = False

    if group_rows:
        routing = GroupRoutingContext.from_config(group_rows, task_id=job.id)
        last_error: Optional[str] = None
        for group_state in routing.group_states:
            group_state.apply_round_robin_start(job.id)
            while group_state.current_order:
                link = group_state.current_order[0]
                preset: LLMEndpointPreset = link.preset
                ok, reason = _preset_eligible_for_grading(preset, need_vision=need_vision)
                if not ok:
                    last_error = reason
                    group_state.remove_member(link)
                    continue
                attempt_limit = max(1, int(preset.max_retries or 0) + 1)
                for request_attempt in range(1, attempt_limit + 1):
                    try:
                        return _request_discussion_completion(
                            preset=preset,
                            messages=messages,
                            max_output_tokens=max_output_tokens,
                            job=job,
                        )
                    except RetryableLLMError as exc:
                        last_error = str(exc)
                        routing.note_failure(group_state, link, exc)
                        if request_attempt >= attempt_limit:
                            break
                        wait_seconds = min(
                            int(preset.initial_backoff_seconds or 2) * (2 ** (request_attempt - 1)),
                            120,
                        )
                        if os.environ.get("LLM_GRADING_TEST_SKIP_BACKOFF") != "1":
                            time.sleep(wait_seconds)
                    except NonRetryableLLMError as exc:
                        last_error = str(exc)
                        routing.note_failure(group_state, link, exc)
                        group_state.remove_member(link)
                        break
        raise NonRetryableLLMError(last_error or "所有组内端点都调用失败。")

    last_error_flat: Optional[str] = None
    for link in sorted(flat_endpoints, key=lambda row: (row.priority, row.id)):
        preset = link.preset
        ok, reason = _preset_eligible_for_grading(preset, need_vision=need_vision)
        if not ok:
            last_error_flat = reason
            continue
        attempt_limit = max(1, int(preset.max_retries or 0) + 1)
        for request_attempt in range(1, attempt_limit + 1):
            try:
                return _request_discussion_completion(
                    preset=preset,
                    messages=messages,
                    max_output_tokens=max_output_tokens,
                    job=job,
                )
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
    raise NonRetryableLLMError(last_error_flat or "所有端点都调用失败。")


def run_discussion_llm_reply_for_job(job_id: int) -> None:
    """Load job in a new session and complete LLM reply (commits internally)."""
    db = SessionLocal()
    try:
        job = db.query(DiscussionLLMJob).filter(DiscussionLLMJob.id == job_id).first()
        if not job or job.status != "pending":
            return
        user_entry = db.query(CourseDiscussionEntry).filter(CourseDiscussionEntry.id == job.user_entry_id).first()
        user = db.query(User).filter(User.id == job.requester_user_id).first()
        if not user_entry or not user:
            job.status = "failed"
            job.error_message = "内部错误：找不到讨论或用户。"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return
        _run_discussion_llm_reply_unlocked(
            db,
            job=job,
            user=user,
            user_body=user_entry.body,
            target_type=job.target_type,
            target_id=job.target_id,
            subject_id=job.subject_id,
            class_id=job.class_id,
        )
    finally:
        db.close()


def _run_discussion_llm_reply_unlocked(
    db: Session,
    *,
    job: DiscussionLLMJob,
    user: User,
    user_body: str,
    target_type: str,
    target_id: int,
    subject_id: int,
    class_id: int,
) -> None:
    def _fail_visible(msg: str, *, release_reservation: bool) -> None:
        if release_reservation:
            release_discussion_quota_reservation(db, job.id)
        job.status = "failed"
        job.error_message = msg
        job.finished_at = datetime.now(timezone.utc)
        sys_user = db.query(User).filter(User.username == "__system_llm_assistant__").first()
        if sys_user:
            assistant_entry = CourseDiscussionEntry(
                target_type=target_type,
                target_id=target_id,
                subject_id=subject_id,
                class_id=class_id,
                author_user_id=sys_user.id,
                body=f"【智能助教】暂无法回复：{msg}",
                message_kind="llm_assistant",
                llm_invocation=False,
            )
            db.add(assistant_entry)
            db.flush()
            job.assistant_entry_id = assistant_entry.id
        db.commit()

    hw: Optional[Homework] = None
    mat: Optional[CourseMaterial] = None
    if target_type == "homework":
        hw = db.query(Homework).filter(Homework.id == target_id).first()
        if not hw:
            _fail_visible("作业不存在。", release_reservation=False)
            return
    else:
        mat = db.query(CourseMaterial).filter(CourseMaterial.id == target_id).first()
        if not mat:
            _fail_visible("资料不存在。", release_reservation=False)
            return

    course = db.query(Subject).filter(Subject.id == subject_id).first()
    if not course:
        _fail_visible("课程不存在。", release_reservation=False)
        return

    try:
        student = resolve_student_for_discussion_llm(db, user, course)
    except ValueError:
        _fail_visible("当前账号无法计费：请使用已绑定学籍的学生账号发起智能助教。", release_reservation=False)
        return

    config = ensure_course_llm_config(db, subject_id, user_id=user.id)
    if not config.is_enabled:
        _fail_visible("当前课程未启用 LLM 配置。", release_reservation=False)
        return
    if not (config.groups or []) and not (config.endpoints or []):
        _fail_visible("当前课程未配置可用端点。", release_reservation=False)
        return

    max_out = max(1, min(8000, int(config.max_output_tokens or 1000)))
    context_parts: list[str] = []
    if hw:
        context_parts.extend(_homework_context_blocks(db, hw, student_id=student.id))
    elif mat:
        context_parts.extend(_material_context_blocks(mat))
    context_text = "\n\n".join(context_parts)
    thread_text = _discussion_thread_text(
        db,
        target_type=target_type,
        target_id=target_id,
        subject_id=subject_id,
        class_id=class_id,
    )
    user_visible = strip_llm_ui_prefix(user_body)
    if not user_visible:
        user_visible = (user_body or "").strip()
    messages = _build_discussion_messages(
        context_text=context_text,
        thread_text=thread_text,
        user_message=user_visible,
        response_language=config.response_language,
    )
    est = _estimate_discussion_prompt_tokens(messages, max_out)
    job.requester_student_id = student.id
    db.flush()

    allowed, err = reserve_discussion_quota_tokens(
        db,
        job,
        config,
        student_id=student.id,
        subject_id=subject_id,
        estimated_tokens=est,
    )
    if not allowed:
        msg = {
            "quota_exceeded_student": "已达到本日学生 token 上限，智能助教未执行。",
        }.get(err or "", "今日额度已用尽，智能助教未执行。")
        _fail_visible(msg, release_reservation=False)
        return

    try:
        result = _call_discussion_with_routing(
            db=db,
            config=config,
            messages=messages,
            max_output_tokens=max_out,
            job=job,
        )
    except NonRetryableLLMError as exc:
        _fail_visible(str(exc) or "LLM 调用失败。", release_reservation=True)
        return
    except Exception as exc:
        _fail_visible(f"LLM 调用异常：{exc}", release_reservation=True)
        return

    sys_user = db.query(User).filter(User.username == "__system_llm_assistant__").first()
    if not sys_user:
        _fail_visible("系统未初始化智能助教账号，请联系管理员。", release_reservation=True)
        return

    reply_body = result["text"]
    usage = result.get("usage") or {}
    assistant_entry = CourseDiscussionEntry(
        target_type=target_type,
        target_id=target_id,
        subject_id=subject_id,
        class_id=class_id,
        author_user_id=sys_user.id,
        body=reply_body,
        message_kind="llm_assistant",
        llm_invocation=False,
    )
    db.add(assistant_entry)
    db.flush()
    job.assistant_entry_id = assistant_entry.id
    job.status = "success"
    job.error_message = None
    job.finished_at = datetime.now(timezone.utc)
    record_discussion_usage_if_needed(db, job, config, student.id, subject_id, usage)
    db.commit()
