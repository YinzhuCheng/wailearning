from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.attachments import (
    get_attachment_download_name,
    get_attachment_file_path,
    save_attachment,
)
from app.auth import get_current_active_user
from app.models import User
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


@router.get("/download")
def download_attachment(
    attachment_url: str,
    attachment_name: Optional[str] = None,
    _current_user: User = Depends(get_current_active_user),
):
    file_path = get_attachment_file_path(attachment_url)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on server.")

    return FileResponse(
        path=file_path,
        filename=get_attachment_download_name(attachment_url, attachment_name),
        media_type="application/octet-stream",
    )
