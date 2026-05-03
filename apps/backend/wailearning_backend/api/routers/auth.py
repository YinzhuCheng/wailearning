from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from apps.backend.wailearning_backend.db.database import get_db
from apps.backend.wailearning_backend.db.models import User
from apps.backend.wailearning_backend.attachments import delete_attachment_file_if_unreferenced, save_attachment
from apps.backend.wailearning_backend.api.schemas import ChangePasswordRequest, MessageResponse, ProfileSelfUpdate, Token, UserCreate, UserResponse
from apps.backend.wailearning_backend.core.auth import verify_password, get_password_hash, create_access_token, get_current_active_user
from apps.backend.wailearning_backend.core.config import settings
from apps.backend.wailearning_backend.course_access import prepare_student_course_context
from apps.backend.wailearning_backend.student_user_roster import sync_student_roster_from_user_accounts
from apps.backend.wailearning_backend.services import LogService
from apps.backend.wailearning_backend.db.models import UserRole

router = APIRouter(prefix="/api/auth", tags=["认证"])


def _client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None or request.client is None:
        return None
    return request.client.host


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db), request: Request = None):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        LogService.log_login(
            db=db,
            user_id=None,
            username=form_data.username,
            ip_address=_client_ip(request),
            user_agent=str(request.headers.get("user-agent")) if request else None,
            success=False
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "tv": int(getattr(user, "token_version", 0) or 0),
        },
        expires_delta=access_token_expires,
    )

    LogService.log_login(
        db=db,
        user_id=user.id,
        username=user.username,
        ip_address=_client_ip(request),
        user_agent=str(request.headers.get("user-agent")) if request else None,
        success=True
    )

    if user.role == UserRole.STUDENT.value and user.class_id:
        prepare_student_course_context(user, db)
        db.commit()

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise HTTPException(status_code=403, detail="Public registration is disabled.")

    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    normalized_role = (user_data.role or "").strip()
    if normalized_role not in {UserRole.STUDENT.value}:
        raise HTTPException(status_code=403, detail="Public registration can only create student accounts.")

    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        hashed_password=hashed_password,
        real_name=user_data.real_name,
        role=UserRole.STUDENT.value,
        class_id=user_data.class_id
    )
    db.add(user)
    db.flush()
    if user.role == UserRole.STUDENT.value and user.class_id:
        sync_student_roster_from_user_accounts(db, [user.id])
    db.commit()
    db.refresh(user)
    return user

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    payload: ProfileSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    data = payload.model_dump(exclude_unset=True)
    if "real_name" in data:
        current_user.real_name = data["real_name"]
    if "discussion_page_size" in data:
        current_user.discussion_page_size = data["discussion_page_size"]
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024


@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    filename = (file.filename or "").strip()
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Avatar must be a JPEG, PNG, GIF, or WebP image.",
        )

    uploaded = await save_attachment(file, request)
    size = int(uploaded.get("size") or 0)
    if size > MAX_AVATAR_BYTES:
        delete_attachment_file_if_unreferenced(db, str(uploaded.get("attachment_url")))
        raise HTTPException(status_code=400, detail="Avatar image must be 2 MB or smaller.")

    previous = current_user.avatar_url
    current_user.avatar_url = str(uploaded["attachment_url"])
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    if previous and previous != current_user.avatar_url:
        delete_attachment_file_if_unreferenced(db, previous)

    return current_user


@router.delete("/me/avatar", response_model=UserResponse)
def remove_my_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    previous = current_user.avatar_url
    if not previous:
        return current_user

    current_user.avatar_url = None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    delete_attachment_file_if_unreferenced(db, previous)
    return current_user


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        LogService.log(
            db=db,
            action="change_password",
            target_type="auth",
            user_id=current_user.id,
            username=current_user.username,
            target_id=current_user.id,
            target_name=current_user.username,
            details="Current password verification failed.",
            ip_address=_client_ip(request),
            user_agent=str(request.headers.get("user-agent")) if request else None,
            result="failed",
        )
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.hashed_password = get_password_hash(payload.new_password)
    current_user.token_version = int(getattr(current_user, "token_version", 0) or 0) + 1
    db.add(current_user)
    db.commit()

    LogService.log(
        db=db,
        action="change_password",
        target_type="auth",
        user_id=current_user.id,
        username=current_user.username,
        target_id=current_user.id,
        target_name=current_user.username,
        details="User changed their own password.",
        ip_address=_client_ip(request),
        user_agent=str(request.headers.get("user-agent")) if request else None,
        result="success"
    )

    return {"message": "Password updated successfully"}
