from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from apps.backend.courseeval_backend.db.models import Student, User, UserRole


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


def get_bound_student_for_user(user: User, db: Session) -> Optional[Student]:
    """
    Resolve the canonical Student row for a student-role User.
    """
    if (user.role or "").strip() != UserRole.STUDENT.value:
        return None

    student_id = getattr(user, "student_id", None)
    if student_id:
        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            if student.class_id and user.class_id != student.class_id:
                user.class_id = student.class_id
                db.flush()
            return student
        user.student_id = None
        db.flush()

    return None


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
        if student_no and db.query(Student.id).filter(Student.student_no == student_no).count() == 1:
            classless_candidates = query.filter(User.class_id.is_(None)).all()
            if len(classless_candidates) == 1:
                return classless_candidates[0]
        return None
    candidates = query.all()
    return candidates[0] if len(candidates) == 1 else None
