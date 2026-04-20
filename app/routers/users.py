from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.attachments import delete_attachment_file_if_unreferenced
from app.auth import get_current_active_user, get_password_hash
from app.database import get_db
from app.models import (
    Class,
    CourseMaterial,
    Homework,
    HomeworkAttempt,
    HomeworkGradingTask,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMTokenUsageLog,
    Notification,
    NotificationRead,
    OperationLog,
    PointExchange,
    PointRecord,
    Student,
    Subject,
    User,
    UserRole,
)
from app.schemas import (
    StudentResponse,
    StudentUserBatchCreateError,
    StudentUserBatchCreateRequest,
    StudentUserBatchCreateResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
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


def delete_user_homeworks(user_id: int, db: Session) -> None:
    homeworks = db.query(Homework).filter(Homework.created_by == user_id).all()
    for homework in homeworks:
        attempts = db.query(HomeworkAttempt).filter(HomeworkAttempt.homework_id == homework.id).all()
        for attempt in attempts:
            if attempt.attachment_url:
                attempt.attachment_url = None
            task_ids = [
                task_id
                for (task_id,) in db.query(HomeworkGradingTask.id)
                .filter(HomeworkGradingTask.attempt_id == attempt.id)
                .all()
            ]
            if task_ids:
                db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
                db.query(HomeworkGradingTask).filter(HomeworkGradingTask.id.in_(task_ids)).delete(
                    synchronize_session=False
                )
            db.query(HomeworkScoreCandidate).filter(HomeworkScoreCandidate.attempt_id == attempt.id).delete(
                synchronize_session=False
            )
            db.delete(attempt)
        for submission in list(homework.submissions):
            submission.attachment_url = None
            db.delete(submission)
        homework.attachment_url = None
        db.delete(homework)


def delete_user_notifications(user_id: int, db: Session) -> None:
    notifications = db.query(Notification).filter(Notification.created_by == user_id).all()
    for notification in notifications:
        delete_attachment_file_if_unreferenced(db, notification.attachment_url)
        db.query(NotificationRead).filter(NotificationRead.notification_id == notification.id).delete(
            synchronize_session=False
        )
        db.delete(notification)


def delete_user_materials(user_id: int, db: Session) -> None:
    materials = db.query(CourseMaterial).filter(CourseMaterial.created_by == user_id).all()
    for material in materials:
        delete_attachment_file_if_unreferenced(db, material.attachment_url)
        db.delete(material)


def build_student_candidate_response(student: Student, class_name: Optional[str]) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        name=student.name,
        student_no=student.student_no,
        gender=student.gender,
        phone=student.phone,
        parent_phone=student.parent_phone,
        address=student.address,
        class_id=student.class_id,
        teacher_id=student.teacher_id,
        created_at=student.created_at,
        class_name=class_name,
        parent_code=student.parent_code,
        has_user=False,
    )


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


@router.get("/student-candidates", response_model=List[StudentResponse])
def get_student_user_candidates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以载入学生用户")

    rows = (
        db.query(Student, Class.name.label("class_name"))
        .join(Class, Class.id == Student.class_id)
        .outerjoin(User, User.username == Student.student_no)
        .filter(User.id.is_(None))
        .order_by(Class.grade.asc(), Class.name.asc(), Student.student_no.asc(), Student.id.asc())
        .all()
    )

    return [build_student_candidate_response(student, class_name) for student, class_name in rows]


@router.post("/student-candidates/load", response_model=StudentUserBatchCreateResponse)
def load_student_users(
    payload: StudentUserBatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以载入学生用户")

    student_ids = list(dict.fromkeys(payload.student_ids))
    if not student_ids:
        raise HTTPException(status_code=400, detail="请至少选择一名学生")

    students = db.query(Student).filter(Student.id.in_(student_ids)).all()
    student_map = {student.id: student for student in students}

    selected_student_nos = {}
    for student in students:
        student_no = (student.student_no or "").strip()
        if student_no:
            selected_student_nos[student_no] = selected_student_nos.get(student_no, 0) + 1

    existing_usernames = set()
    if selected_student_nos:
        existing_usernames = {
            username
            for (username,) in db.query(User.username).filter(User.username.in_(list(selected_student_nos.keys()))).all()
        }

    created_users: List[str] = []
    errors: List[StudentUserBatchCreateError] = []

    try:
        for student_id in student_ids:
            student = student_map.get(student_id)
            if not student:
                errors.append(StudentUserBatchCreateError(student_id=student_id, reason="学生不存在或已被删除"))
                continue

            student_name = (student.name or "").strip()
            student_no = (student.student_no or "").strip()

            if not student_name:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_no=student_no or None,
                        reason="学生姓名为空，无法生成账号",
                    )
                )
                continue

            if not student_no:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_name=student_name,
                        reason="学生学号为空，无法生成账号",
                    )
                )
                continue

            if student.class_id is None:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_name=student_name,
                        student_no=student_no,
                        reason="学生未绑定班级，无法生成账号",
                    )
                )
                continue

            if selected_student_nos.get(student_no, 0) > 1:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_name=student_name,
                        student_no=student_no,
                        reason="该学号在所选学生中重复，无法生成唯一用户名",
                    )
                )
                continue

            if student_no in existing_usernames:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_name=student_name,
                        student_no=student_no,
                        reason="该学生账号已存在",
                    )
                )
                continue

            try:
                with db.begin_nested():
                    user = User(
                        username=student_no,
                        hashed_password=get_password_hash(student_no),
                        real_name=student_name,
                        role=UserRole.STUDENT.value,
                        class_id=student.class_id,
                    )
                    db.add(user)
                    db.flush()
                existing_usernames.add(student_no)
                created_users.append(f"{student_name}（{student_no}）")
            except IntegrityError:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_name=student_name,
                        student_no=student_no,
                        reason="该学生账号已存在或被其他操作占用",
                    )
                )
            except Exception:
                errors.append(
                    StudentUserBatchCreateError(
                        student_id=student.id,
                        student_name=student_name,
                        student_no=student_no,
                        reason="创建失败，请稍后重试",
                    )
                )

        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量载入学生用户失败：{exc}") from exc

    if created_users:
        preview = "、".join(created_users[:20])
        if len(created_users) > 20:
            preview += f" 等 {len(created_users)} 个账号"
        LogService.log(
            db=db,
            action="批量创建",
            target_type="用户",
            user_id=current_user.id,
            username=current_user.username,
            target_name=f"学生用户 {len(created_users)} 个",
            details=f"批量载入学生用户：{preview}",
        )

    return StudentUserBatchCreateResponse(
        total=len(student_ids),
        success=len(created_users),
        failed=len(errors),
        created_users=created_users,
        errors=errors,
    )


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
    db.query(OperationLog).filter(OperationLog.user_id == user.id).update(
        {OperationLog.user_id: None},
        synchronize_session=False,
    )

    db.query(NotificationRead).filter(NotificationRead.user_id == user.id).delete(synchronize_session=False)
    delete_user_homeworks(user.id, db)
    delete_user_notifications(user.id, db)
    delete_user_materials(user.id, db)

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
