"""Bidirectional sync between User (student accounts) and Student (roster rows).

Ensures deployment seeds and admin CRUD stay aligned: student login accounts have
matching roster rows when possible, and roster rows get matching accounts with
username == student_no (same class).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.core.auth import get_password_hash
from apps.backend.wailearning_backend.course_access import prepare_student_course_context, sync_student_course_enrollments
from apps.backend.wailearning_backend.db.models import Student, User, UserRole
from apps.backend.wailearning_backend.student_user_roster import sync_student_roster_from_user_accounts


def _clean(s: object | None) -> str:
    return (str(s).strip() if s is not None else "").strip()


def sync_student_user_from_roster_row(db: Session, student: Student) -> None:
    """Ensure a User row exists and matches this roster (username == student_no, same class). Does not commit."""
    student_no = _clean(student.student_no)
    if not student_no:
        return

    display_name = _clean(student.name) or student_no
    user = db.query(User).filter(User.username == student_no).first()

    if not user:
        db.add(
            User(
                username=student_no,
                hashed_password=get_password_hash(student_no),
                real_name=display_name,
                role=UserRole.STUDENT.value,
                class_id=student.class_id,
                is_active=True,
            )
        )
        db.flush()
        sync_student_course_enrollments(student, db)
        linked = db.query(User).filter(User.username == student_no).first()
        if linked:
            prepare_student_course_context(linked, db)
        return

    if (user.role or "").strip() != UserRole.STUDENT.value:
        user.role = UserRole.STUDENT.value
    if user.class_id != student.class_id:
        user.class_id = student.class_id
    if _clean(user.real_name) != display_name:
        user.real_name = display_name
    if not user.is_active:
        user.is_active = True
    db.flush()
    sync_student_course_enrollments(student, db)
    prepare_student_course_context(user, db)


def sync_student_users_from_roster(db: Session) -> None:
    """For each roster row with student_no, align the corresponding User account."""
    for st in db.query(Student).all():
        if _clean(st.student_no):
            sync_student_user_from_roster_row(db, st)


def sync_roster_from_all_student_users(db: Session):
    """Ensure Student rows exist for every student User."""
    ids = [
        uid
        for (uid,) in db.query(User.id)
        .filter(User.role == UserRole.STUDENT.value, User.class_id.isnot(None))
        .all()
    ]
    if not ids:
        return None
    return sync_student_roster_from_user_accounts(db, ids)


def reconcile_student_users_and_roster(db: Session) -> dict[str, int]:
    """
    Full reconciliation for deployment/migrations.

    1. Users (student) -> roster rows when missing.
    2. Roster rows -> user accounts aligned (names, class, role).

    Does not commit.
    """
    db.flush()
    res = sync_roster_from_all_student_users(db)
    sync_student_users_from_roster(db)
    return {
        "users_to_roster_created": res.created if res else 0,
        "users_to_roster_updated": res.updated if res else 0,
        "users_to_roster_skipped": res.skipped if res else 0,
        "users_to_roster_errors": len(res.errors) if res else 0,
    }
