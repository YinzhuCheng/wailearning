"""Align Student roster rows with student User accounts (username == student_no)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.course_access import prepare_student_course_context
from app.models import Class, Gender, Student, User, UserRole


@dataclass
class RosterUpsertForUserResult:
    """Outcome of upsert_student_roster_for_user for one user."""

    created: int = 0
    updated: int = 0
    skipped: int = 0
    error_reason: Optional[str] = None
    error_username: Optional[str] = None


def upsert_student_roster_for_user(db: Session, user: User) -> RosterUpsertForUserResult:
    """
    Ensure a Student row exists for this student account: student_no == username, class_id == user.class_id.
    Updates display name from user.real_name when needed. Then runs prepare_student_course_context.

    No-op (skipped) for non-students or missing class/username.
    Returns error_reason when the roster cannot be written (e.g. duplicate student_no in another class).
    """
    if (user.role or "").strip() != UserRole.STUDENT.value:
        return RosterUpsertForUserResult(skipped=1)

    if not user.class_id:
        return RosterUpsertForUserResult(skipped=1)

    student_no = (user.username or "").strip()
    if not student_no:
        return RosterUpsertForUserResult(
            error_reason="用户名为空，无法作为学号写入花名册",
            error_username=user.username,
        )

    display_name = (user.real_name or "").strip() or student_no

    existing_same_class = (
        db.query(Student)
        .filter(Student.student_no == student_no, Student.class_id == user.class_id)
        .first()
    )
    if existing_same_class:
        if (existing_same_class.name or "").strip() != display_name:
            existing_same_class.name = display_name
            prepare_student_course_context(user, db)
            return RosterUpsertForUserResult(updated=1)
        prepare_student_course_context(user, db)
        return RosterUpsertForUserResult(skipped=1)

    conflict = (
        db.query(Student)
        .filter(Student.student_no == student_no, Student.class_id != user.class_id)
        .first()
    )
    if conflict:
        return RosterUpsertForUserResult(
            error_reason="该学号已在其他班级的花名册中，请先处理重复或调整班级后再同步",
            error_username=student_no,
        )

    class_obj = db.query(Class).filter(Class.id == user.class_id).first()
    if not class_obj:
        return RosterUpsertForUserResult(
            error_reason="所属班级不存在",
            error_username=student_no,
        )

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
                prepare_student_course_context(user, db)
                return RosterUpsertForUserResult(updated=1)
            prepare_student_course_context(user, db)
            return RosterUpsertForUserResult(skipped=1)
        return RosterUpsertForUserResult(
            error_reason="花名册写入冲突，请重试或检查学号是否重复",
            error_username=student_no,
        )

    prepare_student_course_context(user, db)
    return RosterUpsertForUserResult(created=1)
