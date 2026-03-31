from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_active_user, get_password_hash
from app.database import get_db
from app.models import (
    Class,
    CourseMaterial,
    Homework,
    Notification,
    NotificationRead,
    PointExchange,
    PointRecord,
    Student,
    Subject,
    User,
    UserRole,
)
from app.schemas import UserCreate, UserResponse, UserUpdate
from app.services import LogService

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def is_admin(user: User) -> bool:
    return user.role.lower() == UserRole.ADMIN.value if user.role else False


def normalize_managed_class_id(role: Optional[str], class_id: Optional[int]) -> Optional[int]:
    if role == UserRole.TEACHER.value:
        return None
    return class_id


def validate_class_exists(class_id: Optional[int], db: Session) -> None:
    if not class_id:
        return

    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=400, detail="班级不存在")


@router.get("", response_model=List[UserResponse])
def get_users(
    role: Optional[str] = None,
    class_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以查看用户列表")

    query = db.query(User)

    if role:
        query = query.filter(User.role == role)
    if class_id:
        query = query.filter(User.class_id == class_id)

    return query.all()


@router.post("", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以创建用户")

    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    managed_class_id = normalize_managed_class_id(user_data.role, user_data.class_id)
    validate_class_exists(managed_class_id, db)

    user = User(
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        real_name=user_data.real_name,
        role=user_data.role,
        class_id=managed_class_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    LogService.log_create(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="用户",
        target_id=user.id,
        target_name=f"{user.real_name}({user.username})",
    )

    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权查看该用户")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="无权修改该用户")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    requested_role_change = "role" in user_data.model_fields_set
    requested_class_change = "class_id" in user_data.model_fields_set

    if not is_admin(current_user) and (requested_role_change or requested_class_change):
        raise HTTPException(status_code=403, detail="无权修改权限或班级")

    next_role = user_data.role if requested_role_change else user.role
    next_class_id = (
        normalize_managed_class_id(next_role, user_data.class_id)
        if requested_class_change or next_role == UserRole.TEACHER.value
        else user.class_id
    )
    validate_class_exists(next_class_id, db)

    changes = []
    if user_data.username is not None:
        existing = (
            db.query(User)
            .filter(User.username == user_data.username, User.id != user_id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        changes.append(f"用户名: {user.username} -> {user_data.username}")
        user.username = user_data.username

    if user_data.real_name is not None:
        changes.append(f"姓名: {user.real_name} -> {user_data.real_name}")
        user.real_name = user_data.real_name

    if requested_role_change and is_admin(current_user) and user.role != next_role:
        changes.append(f"角色: {user.role} -> {next_role}")
        user.role = next_role

    if is_admin(current_user) and user.class_id != next_class_id:
        changes.append(f"班级ID: {user.class_id} -> {next_class_id}")
        user.class_id = next_class_id

    if user_data.is_active is not None and is_admin(current_user):
        changes.append(f"状态: {user.is_active} -> {user_data.is_active}")
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    if changes:
        LogService.log_update(
            db=db,
            user_id=current_user.id,
            username=current_user.username,
            target_type="用户",
            target_id=user.id,
            target_name=f"{user.real_name}({user.username})",
            changes=", ".join(changes),
        )

    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以删除用户")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")

    if user.role == UserRole.ADMIN.value:
        raise HTTPException(status_code=400, detail="管理员账号不能删除")

    user_info = f"{user.real_name}({user.username})"

    db.query(Student).filter(Student.teacher_id == user.id).update(
        {Student.teacher_id: None},
        synchronize_session=False,
    )
    db.query(Subject).filter(Subject.teacher_id == user.id).update(
        {Subject.teacher_id: None},
        synchronize_session=False,
    )
    db.query(PointRecord).filter(PointRecord.operator_id == user.id).update(
        {PointRecord.operator_id: None},
        synchronize_session=False,
    )
    db.query(PointExchange).filter(PointExchange.operator_id == user.id).update(
        {PointExchange.operator_id: None},
        synchronize_session=False,
    )

    db.query(NotificationRead).filter(NotificationRead.user_id == user.id).delete(synchronize_session=False)
    db.query(Homework).filter(Homework.created_by == user.id).delete(synchronize_session=False)
    db.query(Notification).filter(Notification.created_by == user.id).delete(synchronize_session=False)
    db.query(CourseMaterial).filter(CourseMaterial.created_by == user.id).delete(synchronize_session=False)

    db.delete(user)
    db.commit()

    LogService.log_delete(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="用户",
        target_id=user_id,
        target_name=user_info,
    )

    return {"message": "用户删除成功"}
