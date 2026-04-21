from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.bootstrap import normalize_legacy_branding
from app.database import get_db
from app.models import SystemSetting, User
from app.schemas import SystemSettingResponse, SystemSettingUpdate, SystemSettingsResponse


router = APIRouter(prefix="/api/settings", tags=["系统设置"])

PUBLIC_SETTING_KEYS = {
    "system_name",
    "login_background",
    "system_logo",
    "system_intro",
    "copyright",
    "use_bing_background",
}


def is_admin(user: User) -> bool:
    return user.role.lower() == "admin" if user.role else False


@router.get("/public", response_model=SystemSettingsResponse)
def get_public_settings(db: Session = Depends(get_db)):
    settings = db.query(SystemSetting).filter(SystemSetting.setting_key.in_(PUBLIC_SETTING_KEYS)).all()
    settings_dict = {item.setting_key: item.setting_value for item in settings}
    settings_dict["system_name"] = normalize_legacy_branding(settings_dict.get("system_name", ""))
    settings_dict["copyright"] = normalize_legacy_branding(settings_dict.get("copyright", ""))

    return SystemSettingsResponse(
        system_name=settings_dict.get("system_name", "BIMSA-CLASS 大学生教学管理系统"),
        login_background=settings_dict.get("login_background", ""),
        system_logo=settings_dict.get("system_logo", ""),
        system_intro=settings_dict.get("system_intro", "面向大学生的教学管理系统"),
        copyright=settings_dict.get("copyright", "(c) 2026 BIMSA-CLASS"),
        use_bing_background=settings_dict.get("use_bing_background", "true").lower() == "true",
    )


@router.get("/all", response_model=List[SystemSettingResponse])
def get_all_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can access system settings.")

    records = db.query(SystemSetting).order_by(SystemSetting.id).all()
    for record in records:
        if record.setting_key in {"system_name", "copyright"}:
            record.setting_value = normalize_legacy_branding(record.setting_value)
    return records


@router.put("/{setting_key}")
def update_setting(
    setting_key: str,
    data: SystemSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can update system settings.")

    setting = db.query(SystemSetting).filter(SystemSetting.setting_key == setting_key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found.")

    setting.setting_value = data.setting_value
    db.commit()
    return {"message": "Setting updated successfully.", "setting_key": setting_key, "value": data.setting_value}


@router.post("/batch-update")
def batch_update_settings(
    settings: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can update system settings.")

    updated = []
    for key, value in settings.items():
        setting = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if setting:
            setting.setting_value = value
            updated.append(key)

    db.commit()
    return {"message": f"Updated {len(updated)} settings.", "updated": updated}
