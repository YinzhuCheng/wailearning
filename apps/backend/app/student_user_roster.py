"""Sync Student roster rows from student User accounts (username = student_no, same class)."""

from __future__ import annotations

from typing import Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.course_access import prepare_student_course_context
from app.models import Class, Gender, Student, User, UserRole
from app.schemas import StudentRosterUpsertFromUsersError, StudentRosterUpsertFromUsersResponse


def sync_student_roster_from_user_accounts(db: Session, user_ids: Iterable[int]) -> StudentRosterUpsertFromUsersResponse:
    """
    Ensure Student rows exist for student users (no commit). Idempotent.
    Callers must commit the session when appropriate.
    """
    ids = list(dict.fromkeys(int(x) for x in user_ids if x is not None))
    if not ids:
        return StudentRosterUpsertFromUsersResponse(total=0, created=0, updated=0, skipped=0, errors=[])

    users = db.query(User).filter(User.id.in_(ids)).all()
    user_map = {u.id: u for u in users}

    created = 0
    updated = 0
    skipped = 0
    errors: list[StudentRosterUpsertFromUsersError] = []

    for uid in ids:
        user = user_map.get(uid)
        if not user:
            errors.append(StudentRosterUpsertFromUsersError(user_id=uid, reason="用户不存在"))
            continue
        if (user.role or "").strip() != UserRole.STUDENT.value:
            errors.append(
                StudentRosterUpsertFromUsersError(
                    user_id=user.id, username=user.username, reason="仅支持学生角色账号"
                )
            )
            continue
        if not user.class_id:
            errors.append(
                StudentRosterUpsertFromUsersError(
                    user_id=user.id,
                    username=user.username,
                    reason="学生账号未分配班级，无法写入花名册",
                )
            )
            continue

        student_no = (user.username or "").strip()
        if not student_no:
            errors.append(
                StudentRosterUpsertFromUsersError(
                    user_id=user.id, username=user.username, reason="用户名为空，无法作为学号写入花名册"
                )
            )
            continue

        display_name = (user.real_name or "").strip() or student_no

        existing_same_class = (
            db.query(Student)
            .filter(Student.student_no == student_no, Student.class_id == user.class_id)
            .first()
        )
        if existing_same_class:
            if (existing_same_class.name or "").strip() != display_name:
                existing_same_class.name = display_name
                updated += 1
            else:
                skipped += 1
            prepare_student_course_context(user, db)
            continue

        conflict = (
            db.query(Student)
            .filter(Student.student_no == student_no, Student.class_id != user.class_id)
            .first()
        )
        if conflict:
            errors.append(
                StudentRosterUpsertFromUsersError(
                    user_id=user.id,
                    username=user.username,
                    reason="该学号已在其他班级的花名册中，请先处理重复或调整班级后再同步",
                )
            )
            continue

        class_obj = db.query(Class).filter(Class.id == user.class_id).first()
        if not class_obj:
            errors.append(
                StudentRosterUpsertFromUsersError(
                    user_id=user.id,
                    username=user.username,
                    reason="所属班级不存在",
                )
            )
            continue

        roster = Student(
            name=display_name,
            student_no=student_no,
            gender=Gender.MALE,
            class_id=user.class_id,
        )
        db.add(roster)
        try:
            with db.begin_nested():
                db.flush()
        except IntegrityError:
            db.expunge(roster)
            raced = (
                db.query(Student)
                .filter(Student.student_no == student_no, Student.class_id == user.class_id)
                .first()
            )
            if raced:
                if (raced.name or "").strip() != display_name:
                    raced.name = display_name
                    updated += 1
                else:
                    skipped += 1
                prepare_student_course_context(user, db)
                continue
            errors.append(
                StudentRosterUpsertFromUsersError(
                    user_id=user.id,
                    username=user.username,
                    reason="花名册写入冲突，请重试或检查学号是否重复",
                )
            )
            continue

        created += 1
        prepare_student_course_context(user, db)

    return StudentRosterUpsertFromUsersResponse(
        total=len(ids),
        created=created,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )
