import re

from app.auth import get_password_hash
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Semester, SystemSetting, User


DEFAULT_SEMESTERS = [
    {"name": "2024-1", "year": 2024},
    {"name": "2024-2", "year": 2024},
    {"name": "2025-1", "year": 2025},
    {"name": "2025-2", "year": 2025},
]

DEFAULT_SYSTEM_SETTINGS = [
    ("system_name", "BIMSA-CLASS", "System display name."),
    ("login_background", "", "Custom login background URL."),
    ("system_logo", "", "Custom system logo URL."),
    ("system_intro", "Class management platform", "Short introduction shown on the login page."),
    ("copyright", "(c) 2026 BIMSA-CLASS", "Footer copyright text."),
    ("use_bing_background", "true", "Whether the login page should use the daily Bing background."),
]

LEGACY_SYSTEM_SETTING_VALUES = {
    "system_name": {"DD-CLASS", "DD-CLASS 班级管理系统"},
    "copyright": {"(c) 2026 DD-CLASS", "© 2024 DD-CLASS"},
}


def normalize_legacy_branding(value: str) -> str:
    if not value:
        return value
    return re.sub(r"dd-class", "BIMSA-CLASS", value, flags=re.IGNORECASE)


def seed_default_admin(db) -> None:
    existing_admin = db.query(User).filter(User.username == settings.INIT_ADMIN_USERNAME).first()
    if existing_admin:
        print(f"Admin user '{settings.INIT_ADMIN_USERNAME}' already exists.")
        return

    admin_user = User(
        username=settings.INIT_ADMIN_USERNAME,
        hashed_password=get_password_hash(settings.INIT_ADMIN_PASSWORD),
        real_name=settings.INIT_ADMIN_REAL_NAME,
        role="admin",
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    print(f"Created bootstrap admin '{settings.INIT_ADMIN_USERNAME}'.")


def seed_default_semesters(db) -> None:
    created = 0
    for semester in DEFAULT_SEMESTERS:
        exists = db.query(Semester).filter(Semester.name == semester["name"]).first()
        if exists:
            continue
        db.add(Semester(name=semester["name"], year=semester["year"], is_active=True))
        created += 1

    if created:
        db.commit()
    print(f"Ensured default semesters. Added {created} item(s).")


def seed_default_system_settings(db) -> None:
    created = 0
    updated = 0
    for key, value, description in DEFAULT_SYSTEM_SETTINGS:
        exists = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
        if exists:
            normalized_value = normalize_legacy_branding(exists.setting_value)
            if exists.setting_value in LEGACY_SYSTEM_SETTING_VALUES.get(key, set()) or normalized_value != exists.setting_value:
                exists.setting_value = normalized_value if normalized_value else value
                exists.description = description
                updated += 1
            continue
        db.add(
            SystemSetting(
                setting_key=key,
                setting_value=value,
                description=description,
            )
        )
        created += 1

    if created or updated:
        db.commit()
    print(f"Ensured default system settings. Added {created} item(s), updated {updated} item(s).")


def bootstrap() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.INIT_DEFAULT_DATA:
            seed_default_admin(db)
            seed_default_semesters(db)
            seed_default_system_settings(db)
        else:
            print("INIT_DEFAULT_DATA is false. Table creation completed without seed data.")
    finally:
        db.close()


if __name__ == "__main__":
    bootstrap()
