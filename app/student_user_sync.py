"""
Keep `Student` roster rows and `User` student accounts aligned automatically.

Convention: student login username equals roster `student_no`; account `class_id`
matches roster `class_id`. Uses the same enrollment hooks as manual sync.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.course_access import prepare_student_course_context, sync_student_course_enrollments
from app.models import CourseEnrollment, Gender, Student, User, UserRole


def _clean(s: Optional[object]) -> str:
    if s is None:
        return ""
    return str(s).strip()


def ensure_user_for_roster_student(db: Session, student: Student) -> None:
    """
    After a roster row exists or changes: ensure a matching student User exists
    (username=student_no, class_id, real_name from roster). Creates user if missing;
    updates real_name / class_id when the linked row is an unambiguous student account.
    """
    student_no = _clean(student.student_no)
    if not student_no or not student.class_id:
        return

    display_name = _clean(student.name) or student_no
    user = db.query(User).filter(User.username == student_no).first()

    if user is not None:
        if (user.role or "").strip() != UserRole.STUDENT.value:
            return
        changed = False
        if _clean(user.real_name) != display_name:
            user.real_name = display_name
            changed = True
        if user.class_id != student.class_id:
            user.class_id = student.class_id
            changed = True
        if changed:
            db.flush()
            prepare_student_course_context(user, db)
        return

    try:
        with db.begin_nested():
            db.add(
                User(
                    username=student_no,
                    hashed_password=get_password_hash(student_no),
                    real_name=display_name,
                    role=UserRole.STUDENT.value,
                    class_id=student.class_id,
                )
            )
            db.flush()
    except IntegrityError:
        return

    new_user = db.query(User).filter(User.username == student_no).first()
    if new_user:
        prepare_student_course_context(new_user, db)


def sync_user_from_roster_student(
    db: Session,
    student: Student,
    *,
    previous_student_no: Optional[str] = None,
) -> None:
    """
    When roster student_no / class / name changed: move or create the linked User.
    If previous_student_no is set and differs, re-key username from old to new when safe.
    """
    prev = _clean(previous_student_no) if previous_student_no else ""
    cur = _clean(student.student_no)
    if not cur or not student.class_id:
        return

    display_name = _clean(student.name) or cur

    if prev and prev != cur:
        old_user = db.query(User).filter(User.username == prev).first()
        if old_user and (old_user.role or "").strip() == UserRole.STUDENT.value:
            conflict = db.query(User).filter(User.username == cur, User.id != old_user.id).first()
            if not conflict:
                old_user.username = cur
                old_user.real_name = display_name
                old_user.class_id = student.class_id
                db.flush()
                prepare_student_course_context(old_user, db)
                return

    ensure_user_for_roster_student(db, student)


def sync_roster_from_student_user(
    db: Session,
    user: User,
    *,
    orig_username: Optional[str] = None,
    orig_class_id: Optional[int] = None,
) -> None:
    """
    After creating/updating a student User: ensure a matching Student roster row.
    orig_* capture identity before an in-place update so we can find the roster row
    when username or class changed.
    """
    if (user.role or "").strip() != UserRole.STUDENT.value:
        return

    un = _clean(user.username)
    if not un or not user.class_id:
        return

    display_name = _clean(user.real_name) or un
    ou = _clean(orig_username) if orig_username is not None else un
    oc = orig_class_id if orig_class_id is not None else user.class_id

    st = (
        db.query(Student)
        .filter(Student.student_no == un, Student.class_id == user.class_id)
        .first()
    )
    if st:
        if _clean(st.name) != display_name:
            st.name = display_name
            db.flush()
        prepare_student_course_context(user, db)
        return

    if ou != un or oc != user.class_id:
        st_old = (
            db.query(Student)
            .filter(Student.student_no == ou, Student.class_id == oc)
            .first()
        )
        if st_old:
            if ou != un:
                dup = (
                    db.query(Student)
                    .filter(
                        Student.student_no == un,
                        Student.class_id == user.class_id,
                        Student.id != st_old.id,
                    )
                    .first()
                )
                if dup:
                    prepare_student_course_context(user, db)
                    return
                st_old.student_no = un
            if st_old.class_id != user.class_id:
                db.query(CourseEnrollment).filter(CourseEnrollment.student_id == st_old.id).delete(
                    synchronize_session=False
                )
                st_old.class_id = user.class_id
                db.flush()
                sync_student_course_enrollments(st_old, db)
            st_old.name = display_name
            db.flush()
            prepare_student_course_context(user, db)
            return

    other = db.query(Student).filter(Student.student_no == un, Student.class_id != user.class_id).first()
    if other:
        prepare_student_course_context(user, db)
        return

    try:
        with db.begin_nested():
            roster = Student(
                name=display_name,
                student_no=un,
                gender=Gender.MALE,
                class_id=user.class_id,
            )
            db.add(roster)
            db.flush()
    except IntegrityError:
        prepare_student_course_context(user, db)
        return

    sync_student_course_enrollments(roster, db)
    db.flush()
    prepare_student_course_context(user, db)
