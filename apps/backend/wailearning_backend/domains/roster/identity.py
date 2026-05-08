from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.db.models import Student, User, UserRole


def clean_student_text(value: object | None) -> str:
    return (str(value).strip() if value is not None else "").strip()


def generate_student_no(db: Session) -> str:
    """Generate a unique temporary student number for roster imports without one."""
    prefix = f"SYS{datetime.now(timezone.utc):%Y%m%d}"
    existing = {
        row[0]
        for row in db.query(Student.student_no)
        .filter(Student.student_no.like(f"{prefix}%"))
        .all()
        if row[0]
    }
    for obj in tuple(db.new):
        if isinstance(obj, Student) and obj.student_no:
            existing.add(str(obj.student_no))

    next_index = len(existing) + 1
    while True:
        candidate = f"{prefix}{next_index:04d}"
        if candidate not in existing:
            return candidate
        next_index += 1


def get_bound_student_for_user(user: User, db: Session, *, bind_legacy: bool = True) -> Optional[Student]:
    """
    Resolve the canonical Student row for a student-role User.

    New data uses users.student_id. Legacy data is still recovered by
    username/student_no and class_id, then backfilled into users.student_id.
    """
    if (user.role or "").strip() != UserRole.STUDENT.value:
        return None

    student_id = getattr(user, "student_id", None)
    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            if student.class_id and user.class_id != student.class_id:
                user.class_id = student.class_id
                if bind_legacy:
                    db.flush()
            return student
        user.student_id = None
        if bind_legacy:
            db.flush()

    username = clean_student_text(user.username)
    if not username:
        return None

    query = db.query(Student).filter(Student.student_no == username)
    if user.class_id:
        student = query.filter(Student.class_id == user.class_id).first()
        if not student:
            return None
    else:
        student = query.first() if query.count() == 1 else None

    if student and bind_legacy:
        already_bound = (
            db.query(User)
            .filter(User.student_id == student.id, User.id != user.id)
            .first()
        )
        if not already_bound:
            user.student_id = student.id
            if student.class_id and user.class_id != student.class_id:
                user.class_id = student.class_id
            db.flush()

    return student


def find_user_for_student(db: Session, student: Student) -> Optional[User]:
    if student.id:
        user = (
            db.query(User)
            .filter(User.role == UserRole.STUDENT.value, User.student_id == student.id)
            .first()
        )
        if user:
            return user

    student_no = clean_student_text(student.student_no)
    if not student_no:
        return None

    query = db.query(User).filter(
        User.role == UserRole.STUDENT.value,
        User.username == student_no,
    )
    if student.class_id:
        same_class_user = query.filter(User.class_id == student.class_id).first()
        if same_class_user:
            return same_class_user
    candidates = query.all()
    return candidates[0] if len(candidates) == 1 else None


def student_has_user(db: Session, student: Student) -> bool:
    if (
        student.id
        and db.query(User.id)
        .filter(User.role == UserRole.STUDENT.value, User.student_id == student.id)
        .first()
    ):
        return True
    student_no = clean_student_text(student.student_no)
    if not student_no:
        return False
    query = db.query(User.id).filter(
        User.role == UserRole.STUDENT.value,
        User.username == student_no,
    )
    if student.class_id:
        query = query.filter(User.class_id == student.class_id)
    return query.first() is not None


def backfill_student_user_bindings(db: Session) -> int:
    updated = 0
    users = db.query(User).filter(User.role == UserRole.STUDENT.value).all()
    for user in users:
        before = getattr(user, "student_id", None)
        get_bound_student_for_user(user, db, bind_legacy=True)
        if getattr(user, "student_id", None) and getattr(user, "student_id", None) != before:
            updated += 1
    return updated
