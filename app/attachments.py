from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
ATTACHMENTS_DIR = UPLOADS_DIR / "attachments"
MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
BLOCKED_ATTACHMENT_EXTENSIONS = {
    ".apk",
    ".app",
    ".bat",
    ".cmd",
    ".com",
    ".exe",
    ".msi",
    ".ps1",
    ".scr",
}
BLOCKED_ATTACHMENT_CONTENT_TYPES = {
    "application/x-msdownload",
    "application/x-msdos-program",
    "application/vnd.microsoft.portable-executable",
}


def ensure_upload_directories() -> None:
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_attachment_upload(file: UploadFile) -> str:
    filename = (file.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Please select a file to upload.")

    extension = Path(filename).suffix.lower()
    if extension in BLOCKED_ATTACHMENT_EXTENSIONS or file.content_type in BLOCKED_ATTACHMENT_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Executable files are not allowed.")

    return extension


async def save_attachment(file: UploadFile, request: Request) -> dict[str, object]:
    ensure_upload_directories()
    extension = validate_attachment_upload(file)
    content = await file.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if size > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=400, detail="Attachment size must be 20 MB or smaller.")

    stored_name = f"{uuid4().hex}{extension}"
    target_path = ATTACHMENTS_DIR / stored_name
    target_path.write_bytes(content)

    return {
        "attachment_name": file.filename,
        "attachment_url": str(request.url_for("uploads", path=f"attachments/{stored_name}")),
        "content_type": file.content_type,
        "size": size,
    }


def delete_attachment_file(attachment_url: str | None) -> None:
    target_path = get_attachment_file_path(attachment_url)
    if not target_path:
        return
    if target_path.exists():
        target_path.unlink()


def get_attachment_file_path(attachment_url: str | None) -> Path | None:
    if not attachment_url:
        return None

    parsed_url = urlparse(attachment_url)
    attachment_path = unquote(parsed_url.path or "")
    prefix = "/uploads/attachments/"
    if not attachment_path.startswith(prefix):
        return None

    stored_name = Path(attachment_path[len(prefix):]).name
    return ATTACHMENTS_DIR / stored_name
