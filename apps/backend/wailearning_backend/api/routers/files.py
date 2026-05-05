import logging
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.attachments import (
    get_attachment_download_name,
    get_attachment_file_path,
    get_attachment_stored_name,
    save_attachment,
)
from apps.backend.wailearning_backend.core.auth import get_current_active_user
from apps.backend.wailearning_backend.domains.courses.access import ensure_course_access
from apps.backend.wailearning_backend.db.database import get_db
from apps.backend.wailearning_backend.db.models import CourseMaterial, Homework, HomeworkAttempt, HomeworkSubmission, Notification, Subject, User, UserRole
from apps.backend.wailearning_backend.api.routers.classes import get_accessible_class_ids
from apps.backend.wailearning_backend.api.schemas import AttachmentUploadResponse


router = APIRouter(prefix="/api/files", tags=["文件上传"])
_log = logging.getLogger(__name__)


@router.post("/upload", response_model=AttachmentUploadResponse)
async def upload_attachment(
    request: Request,
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_active_user),
):
    uploaded = await save_attachment(file, request)
    return AttachmentUploadResponse(**uploaded)


def _has_attachment_access(current_user: User, attachment_url: str, db: Session) -> bool:
    if current_user.avatar_url and attachment_url == current_user.avatar_url:
        return True

    allowed_class_ids = set(get_accessible_class_ids(current_user, db))

    homework = db.query(Homework).filter(Homework.attachment_url == attachment_url).first()
    if homework:
        if current_user.role == UserRole.ADMIN or homework.class_id in allowed_class_ids:
            if homework.subject_id:
                try:
                    ensure_course_access(homework.subject_id, current_user, db)
                except (ValueError, PermissionError):
                    return False
            return True
        return False

    material = db.query(CourseMaterial).filter(CourseMaterial.attachment_url == attachment_url).first()
    if material:
        if current_user.role == UserRole.ADMIN or material.class_id in allowed_class_ids:
            if material.subject_id:
                try:
                    ensure_course_access(material.subject_id, current_user, db)
                except (ValueError, PermissionError):
                    return False
            return True
        return False

    notification = db.query(Notification).filter(Notification.attachment_url == attachment_url).first()
    if notification:
        if current_user.role == UserRole.ADMIN:
            return True
        if notification.class_id and notification.class_id not in allowed_class_ids:
            return False
        if notification.subject_id:
            try:
                ensure_course_access(notification.subject_id, current_user, db)
            except (ValueError, PermissionError):
                return False
        return True

    submission = db.query(HomeworkSubmission).filter(HomeworkSubmission.attachment_url == attachment_url).first()
    if submission:
        if current_user.role == UserRole.STUDENT:
            return submission.student is not None and submission.student.student_no == current_user.username
        if current_user.role == UserRole.ADMIN or submission.class_id in allowed_class_ids:
            if submission.subject_id:
                try:
                    ensure_course_access(submission.subject_id, current_user, db)
                except (ValueError, PermissionError):
                    return False
            return True
        return False

    attempt = db.query(HomeworkAttempt).filter(HomeworkAttempt.attachment_url == attachment_url).first()
    if attempt:
        if current_user.role == UserRole.STUDENT:
            return attempt.student is not None and attempt.student.student_no == current_user.username
        if current_user.role == UserRole.ADMIN or attempt.class_id in allowed_class_ids:
            if attempt.subject_id:
                try:
                    ensure_course_access(attempt.subject_id, current_user, db)
                except (ValueError, PermissionError):
                    return False
            return True
        return False

    subject_cover = db.query(Subject).filter(Subject.cover_image_url == attachment_url).first()
    if subject_cover:
        try:
            ensure_course_access(subject_cover.id, current_user, db)
        except (ValueError, PermissionError):
            return False
        return True

    return False


def _attachment_urls_with_exact_stored_basename(db: Session, stored_basename: str) -> list[str]:
    """All DB attachment_url values whose parsed stored file name exactly matches (no full-table scan)."""
    if not stored_basename or Path(stored_basename).name in {"", ".", "..", "attachments"}:
        return []
    urls: list[str] = []
    suffixes = (
        f"/{stored_basename}",
        f"\\{stored_basename}",
        stored_basename,
    )
    for model in (HomeworkSubmission, HomeworkAttempt, Homework, CourseMaterial, Notification):
        if not hasattr(model, "attachment_url"):
            continue
        conditions = [model.attachment_url.endswith(s) for s in suffixes]
        q = db.query(model.attachment_url).filter(model.attachment_url.isnot(None), or_(*conditions))
        for (u,) in q.all():
            if u and get_attachment_stored_name(str(u)) == stored_basename:
                urls.append(str(u))
    user_rows = (
        db.query(User.avatar_url)
        .filter(User.avatar_url.isnot(None), or_(*[User.avatar_url.endswith(s) for s in suffixes]))
        .all()
    )
    for (u,) in user_rows:
        if u and get_attachment_stored_name(str(u)) == stored_basename:
            urls.append(str(u))
    sub_rows = (
        db.query(Subject.cover_image_url)
        .filter(Subject.cover_image_url.isnot(None), or_(*[Subject.cover_image_url.endswith(s) for s in suffixes]))
        .all()
    )
    for (u,) in sub_rows:
        if u and get_attachment_stored_name(str(u)) == stored_basename:
            urls.append(str(u))
    return urls


@router.get("/download/{stored_name:path}", name="download_attachment_by_name")
def download_attachment_by_stored_name(
    stored_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Serves a file from storage by the stored file name; access matches DB-referenced attachment URLs."""
    safe_name = unquote(stored_name).strip().replace("\\", "/")
    if not safe_name or Path(safe_name).name in {"", ".", "..", "attachments"}:
        raise HTTPException(status_code=404, detail="Attachment file not found on server.")
    target_base = Path(safe_name).name
    candidates = _attachment_urls_with_exact_stored_basename(db, target_base)
    if not candidates:
        raise HTTPException(status_code=404, detail="Attachment file not found on server.")
    allowed = [u for u in candidates if _has_attachment_access(current_user, u, db)]
    if not allowed:
        raise HTTPException(status_code=403, detail="You do not have access to this attachment.")

    paths: list[Path] = []
    for u in allowed:
        p = get_attachment_file_path(u)
        if not p or not p.exists():
            raise HTTPException(status_code=404, detail="Attachment file not found on server.")
        try:
            paths.append(p.resolve())
        except OSError:
            paths.append(p)
    unique_paths = {str(p) for p in paths}
    if len(unique_paths) != 1:
        _log.warning(
            "attachment basename collision with differing files: user=%s basename=%s paths=%s",
            getattr(current_user, "id", None),
            target_base,
            sorted(unique_paths),
        )
        raise HTTPException(
            status_code=403,
            detail="Ambiguous attachment reference; use the full download URL from the application.",
        )

    url = sorted(allowed)[0]
    file_path = paths[0]

    return FileResponse(
        path=file_path,
        filename=get_attachment_download_name(url, None),
        media_type="application/octet-stream",
    )


@router.get("/download")
def download_attachment(
    attachment_url: str,
    attachment_name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not _has_attachment_access(current_user, attachment_url, db):
        raise HTTPException(status_code=403, detail="You do not have access to this attachment.")

    file_path = get_attachment_file_path(attachment_url)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on server.")

    return FileResponse(
        path=file_path,
        filename=get_attachment_download_name(attachment_url, attachment_name),
        media_type="application/octet-stream",
    )
