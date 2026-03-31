from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.attachments import save_attachment
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
