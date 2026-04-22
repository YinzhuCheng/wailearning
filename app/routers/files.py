from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.attachments import (
    get_attachment_download_name,
    get_attachment_file_path,
    save_attachment,
)
from app.auth import get_current_active_user
from app.course_access import ensure_course_access
from app.database import get_db
from app.models import CourseMaterial, Homework, HomeworkAttempt, HomeworkSubmission, Notification, User, UserRole
from app.routers.classes import get_accessible_class_ids
from app.schemas import AttachmentUploadResponse


router = APIRouter(prefix="/api/files", tags=["文件上传"])


@router.post("/upload", response_model=AttachmentUploadResponse)
async def upload_attachment(
    request: Request,
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_active_user),
):
    uploaded = await save_attachment(file, request)
    return AttachmentUploadResponse(**uploaded)


def _has_attachment_access(current_user: User, attachment_url: str, db: Session) -> bool:
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

    return False


def _first_attachment_url_for_stored_name(db: Session, stored_name: str) -> Optional[str]:
    """Find a row whose attachment_url ends with the stored file name (uuid + ext)."""
    if not stored_name or Path(stored_name).name in {"", ".", "..", "attachments"}:
        return None
    like_pattern = f"%{Path(unquote(stored_name)).name}"
    for model in (HomeworkSubmission, HomeworkAttempt, Homework, CourseMaterial, Notification):
        if not hasattr(model, "attachment_url"):
            continue
        row = (
            db.query(model)
            .filter(model.attachment_url.isnot(None), model.attachment_url.like(like_pattern))
            .first()
        )
        if row and getattr(row, "attachment_url", None):
            return str(row.attachment_url)
    return None


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
    url = _first_attachment_url_for_stored_name(db, safe_name)
    if not url:
        raise HTTPException(status_code=404, detail="Attachment file not found on server.")
    if not _has_attachment_access(current_user, url, db):
        raise HTTPException(status_code=403, detail="You do not have access to this attachment.")

    file_path = get_attachment_file_path(url)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on server.")

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
