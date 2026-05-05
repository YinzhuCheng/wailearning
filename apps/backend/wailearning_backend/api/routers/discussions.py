"""Course-scoped discussions on homework and materials (linear thread, paginated)."""

from __future__ import annotations

import threading
from typing import Literal, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc
from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.core.auth import get_current_active_user
from apps.backend.wailearning_backend.domains.courses.access import ensure_course_access_http, is_course_instructor
from apps.backend.wailearning_backend.db.database import get_db
from apps.backend.wailearning_backend.db.models import CourseDiscussionEntry, CourseMaterial, DiscussionLLMJob, Homework, Subject, User, UserRole
from apps.backend.wailearning_backend.domains.llm.discussion_ui import strip_llm_ui_prefix
from apps.backend.wailearning_backend.api.routers.classes import get_accessible_class_ids
from apps.backend.wailearning_backend.api.schemas import (
    CourseDiscussionCreate,
    CourseDiscussionEntryResponse,
    CourseDiscussionListResponse,
)

router = APIRouter(prefix="/api/discussions", tags=["课程讨论"])

DEFAULT_PAGE_SIZE = 10
MIN_PAGE_SIZE = 5
MAX_PAGE_SIZE = 50
MAX_BODY_LEN = 8000

TargetType = Literal["homework", "material"]


def _run_discussion_llm_job(job_id: int) -> None:
    from apps.backend.wailearning_backend.llm_discussion import run_discussion_llm_reply_for_job

    run_discussion_llm_reply_for_job(job_id)


def _resolve_page_size(user: User, page_size: Optional[int]) -> int:
    if page_size is not None:
        return max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, int(page_size)))
    pref = user.discussion_page_size
    if pref is not None:
        return max(MIN_PAGE_SIZE, min(MAX_PAGE_SIZE, int(pref)))
    return DEFAULT_PAGE_SIZE


def _load_homework(db: Session, homework_id: int) -> Homework:
    row = db.query(Homework).filter(Homework.id == homework_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Homework not found.")
    return row


def _load_material(db: Session, material_id: int) -> CourseMaterial:
    row = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Material not found.")
    return row


def _ensure_course_instance(
    *,
    subject_id: int,
    class_id: int,
    current_user: User,
    db: Session,
) -> Subject:
    course = ensure_course_access_http(subject_id, current_user, db)
    if course.class_id is not None and int(course.class_id) != int(class_id):
        raise HTTPException(status_code=400, detail="class_id does not match this course instance.")
    allowed = get_accessible_class_ids(current_user, db)
    if current_user.role != UserRole.ADMIN and int(class_id) not in allowed:
        raise HTTPException(status_code=403, detail="You do not have access to this class.")
    return course


def _ensure_homework_discussion_scope(
    homework: Homework,
    *,
    subject_id: int,
    class_id: int,
    current_user: User,
    db: Session,
) -> None:
    _ensure_course_instance(subject_id=subject_id, class_id=class_id, current_user=current_user, db=db)
    if homework.subject_id is None or int(homework.subject_id) != int(subject_id):
        raise HTTPException(status_code=400, detail="subject_id does not match this homework.")
    if int(homework.class_id) != int(class_id):
        raise HTTPException(status_code=400, detail="class_id does not match this homework.")


def _ensure_material_discussion_scope(
    material: CourseMaterial,
    *,
    subject_id: int,
    class_id: int,
    current_user: User,
    db: Session,
) -> None:
    _ensure_course_instance(subject_id=subject_id, class_id=class_id, current_user=current_user, db=db)
    if material.subject_id is None or int(material.subject_id) != int(subject_id):
        raise HTTPException(status_code=400, detail="subject_id does not match this material.")
    if int(material.class_id) != int(class_id):
        raise HTTPException(status_code=400, detail="class_id does not match this material.")


def _can_delete_entry(entry: CourseDiscussionEntry, current_user: User, db: Session) -> bool:
    if current_user.role == UserRole.ADMIN:
        return True
    if entry.author_user_id == current_user.id:
        return True
    course = db.query(Subject).filter(Subject.id == entry.subject_id).first()
    if course and is_course_instructor(current_user, course):
        return True
    return False


def _serialize_entry(row: CourseDiscussionEntry, author: User) -> CourseDiscussionEntryResponse:
    return CourseDiscussionEntryResponse(
        id=row.id,
        target_type=row.target_type,
        target_id=row.target_id,
        subject_id=row.subject_id,
        class_id=row.class_id,
        author_user_id=row.author_user_id,
        author_real_name=author.real_name,
        author_username=author.username,
        author_role=author.role,
        body=row.body,
        body_format=getattr(row, "body_format", None) or "markdown",
        message_kind=getattr(row, "message_kind", None) or "human",
        llm_invocation=bool(getattr(row, "llm_invocation", False)),
        created_at=row.created_at,
    )


@router.get("", response_model=CourseDiscussionListResponse)
def list_discussion(
    target_type: TargetType = Query(..., description="homework or material"),
    target_id: int = Query(..., ge=1),
    subject_id: int = Query(..., ge=1),
    class_id: int = Query(..., ge=1),
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    size = _resolve_page_size(current_user, page_size)

    if target_type == "homework":
        hw = _load_homework(db, target_id)
        _ensure_homework_discussion_scope(hw, subject_id=subject_id, class_id=class_id, current_user=current_user, db=db)
    else:
        mat = _load_material(db, target_id)
        _ensure_material_discussion_scope(mat, subject_id=subject_id, class_id=class_id, current_user=current_user, db=db)

    q = (
        db.query(CourseDiscussionEntry, User)
        .join(User, User.id == CourseDiscussionEntry.author_user_id)
        .filter(
            CourseDiscussionEntry.target_type == target_type,
            CourseDiscussionEntry.target_id == target_id,
            CourseDiscussionEntry.subject_id == subject_id,
            CourseDiscussionEntry.class_id == class_id,
        )
    )
    total = q.count()
    rows: Tuple[CourseDiscussionEntry, User] = (
        q.order_by(asc(CourseDiscussionEntry.created_at), asc(CourseDiscussionEntry.id))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return CourseDiscussionListResponse(
        page=page,
        page_size=size,
        total=total,
        data=[_serialize_entry(e, u) for e, u in rows],
    )


@router.post("", response_model=CourseDiscussionEntryResponse)
def create_discussion(
    payload: CourseDiscussionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="body cannot be empty.")
    if len(body) > MAX_BODY_LEN:
        raise HTTPException(status_code=400, detail=f"body exceeds {MAX_BODY_LEN} characters.")

    if payload.target_type == "homework":
        hw = _load_homework(db, payload.target_id)
        _ensure_homework_discussion_scope(
            hw,
            subject_id=payload.subject_id,
            class_id=payload.class_id,
            current_user=current_user,
            db=db,
        )
    else:
        mat = _load_material(db, payload.target_id)
        _ensure_material_discussion_scope(
            mat,
            subject_id=payload.subject_id,
            class_id=payload.class_id,
            current_user=current_user,
            db=db,
        )

    invoke_llm = bool(payload.invoke_llm)
    if invoke_llm and current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="仅学生账号可发起智能助教回复。")

    body_for_display = body
    llm_invocation = False
    if invoke_llm:
        inner = strip_llm_ui_prefix(body)
        if not inner:
            raise HTTPException(status_code=400, detail="智能助教模式下请填写具体问题或说明（@LLM 之后的内容不能为空）。")
        llm_invocation = True

    entry = CourseDiscussionEntry(
        target_type=payload.target_type,
        target_id=payload.target_id,
        subject_id=payload.subject_id,
        class_id=payload.class_id,
        author_user_id=current_user.id,
        body=body_for_display,
        body_format=payload.body_format,
        message_kind="human",
        llm_invocation=llm_invocation,
    )
    db.add(entry)
    db.flush()

    job_id: Optional[int] = None
    if invoke_llm:
        job = DiscussionLLMJob(
            subject_id=payload.subject_id,
            class_id=payload.class_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            requester_user_id=current_user.id,
            user_entry_id=entry.id,
            status="pending",
        )
        db.add(job)
        db.flush()
        job_id = job.id

    db.commit()
    db.refresh(entry)

    if job_id is not None:
        threading.Thread(target=_run_discussion_llm_job, args=(job_id,), daemon=True).start()

    return _serialize_entry(entry, current_user)


@router.delete("/{entry_id}", status_code=204)
def delete_discussion(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    row = db.query(CourseDiscussionEntry).filter(CourseDiscussionEntry.id == entry_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Discussion entry not found.")

    if row.target_type == "homework":
        hw = _load_homework(db, row.target_id)
        _ensure_homework_discussion_scope(hw, subject_id=row.subject_id, class_id=row.class_id, current_user=current_user, db=db)
    else:
        mat = _load_material(db, row.target_id)
        _ensure_material_discussion_scope(mat, subject_id=row.subject_id, class_id=row.class_id, current_user=current_user, db=db)

    if not _can_delete_entry(row, current_user, db):
        raise HTTPException(status_code=403, detail="You cannot delete this message.")

    db.delete(row)
    db.commit()
    return None
