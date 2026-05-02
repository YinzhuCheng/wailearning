from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models import Class, CourseEnrollment, CourseEnrollmentBlock, Student, Subject, User, UserRole


def subject_teacher_user_ids(db: Session, subject_id: int) -> list[int]:
    """Notify course teacher plus class teachers for the subject's class."""
    course = db.query(Subject).filter(Subject.id == subject_id).first()
    if not course:
        return []
    ids: list[int] = []
    if course.teacher_id:
        ids.append(int(course.teacher_id))
    if course.class_id:
        class_teachers = (
            db.query(User.id)
            .filter(User.role == UserRole.CLASS_TEACHER.value, User.class_id == course.class_id)
            .all()
        )
        ids.extend(int(r[0]) for r in class_teachers)
    return sorted(set(ids))


def _pending_course_enrollment_subject_ids(db: Session, student_id: int) -> set[int]:
    subject_ids: set[int] = set()
    for obj in tuple(db.identity_map.values()) + tuple(db.new):
        if isinstance(obj, CourseEnrollment) and getattr(obj, "student_id", None) == student_id and obj.subject_id:
            subject_ids.add(int(obj.subject_id))
    return subject_ids


def prepare_student_course_context(user: User, db: Session) -> None:
    """
    For student accounts: align roster class with account class when unambiguous,
    then ensure CourseEnrollment rows exist for all courses in that class.

    Idempotent aside from one-time roster class_id correction when username matches
    exactly one Student row in another class.
    """
    if user.role != UserRole.STUDENT or not user.username or not user.class_id:
        return

    roster_matches = db.query(Student).filter(Student.student_no == user.username).all()
    if len(roster_matches) == 1:
        st = roster_matches[0]
        if st.class_id != user.class_id:
            db.query(CourseEnrollment).filter(CourseEnrollment.student_id == st.id).delete(synchronize_session=False)
            st.class_id = user.class_id
            db.flush()

    student = get_student_profile_for_user(user, db)
    if student:
        sync_student_course_enrollments(student, db, respect_enrollment_blocks=True)
    db.flush()


def get_student_profile_for_user(user: User, db: Session) -> Optional[Student]:
    """Roster student for this login: same class as the account and student_no == username."""
    if not user.username or not user.class_id:
        return None
    return (
        db.query(Student)
        .filter(Student.student_no == user.username, Student.class_id == user.class_id)
        .first()
    )


def get_accessible_courses_query(user: User, db: Session):
    query = db.query(Subject)

    if user.role == UserRole.ADMIN:
        return query

    if user.role == UserRole.STUDENT:
        prepare_student_course_context(user, db)
        db.commit()

        student = get_student_profile_for_user(user, db)
        if not student:
            return query.filter(False)
        enrolled_subject_ids = [
            row[0]
            for row in db.query(CourseEnrollment.subject_id)
            .filter(CourseEnrollment.student_id == student.id)
            .all()
        ]
        visible_ids = sorted(set(enrolled_subject_ids))
        if not visible_ids:
            return query.filter(False)
        return query.filter(Subject.id.in_(visible_ids))

    if user.role == UserRole.TEACHER:
        return query.filter(Subject.teacher_id == user.id)

    if user.role == UserRole.CLASS_TEACHER:
        class_course_query = query
        if user.class_id:
            class_course_query = query.filter(Subject.class_id == user.class_id)
        else:
            class_course_query = query.filter(False)
        return class_course_query.union(query.filter(Subject.teacher_id == user.id))

    return query.filter(False)


def get_student_elective_catalog_query(user: User, db: Session):
    """
    Active elective courses system-wide for voluntary student enrollment.
    Restricted to students with a resolved roster profile and account class_id.
    """
    query = db.query(Subject)
    if user.role != UserRole.STUDENT:
        return query.filter(False)
    prepare_student_course_context(user, db)
    db.commit()
    student = get_student_profile_for_user(user, db)
    if not student or not user.class_id:
        return query.filter(False)
    return query.filter(
        Subject.status == "active",
        Subject.course_type == "elective",
        Subject.class_id.isnot(None),
    )


def get_student_course_catalog_query(user: User, db: Session):
    """
    All active courses for browse + enrollment hints.
    Electives: self-enroll only when course.class_id matches student's roster class.
    """
    query = db.query(Subject)
    if user.role != UserRole.STUDENT:
        return query.filter(False)
    prepare_student_course_context(user, db)
    db.commit()
    student = get_student_profile_for_user(user, db)
    if not student or not user.class_id:
        return query.filter(False)
    return query.filter(Subject.status == "active")


def get_accessible_course_ids(user: User, db: Session) -> list[int]:
    return [course.id for course in get_accessible_courses_query(user, db).all() if course.id]


def get_accessible_class_ids_from_courses(user: User, db: Session) -> list[int]:
    if user.role == UserRole.ADMIN:
        return [class_obj.id for class_obj in db.query(Class).all()]

    class_ids = set()
    if user.role == UserRole.CLASS_TEACHER and user.class_id:
        class_ids.add(user.class_id)
    if user.role == UserRole.STUDENT and user.class_id:
        class_ids.add(user.class_id)

    for course in get_accessible_courses_query(user, db).all():
        if course.class_id:
            class_ids.add(course.class_id)

    return sorted(class_ids)


def get_course_or_404(course_id: int, db: Session) -> Subject:
    course = db.query(Subject).filter(Subject.id == course_id).first()
    if not course:
        raise ValueError("Course not found.")
    return course


def ensure_course_access(course_id: int, user: User, db: Session) -> Subject:
    course = get_course_or_404(course_id, db)
    accessible_course_ids = get_accessible_course_ids(user, db)
    if course.id not in accessible_course_ids:
        raise PermissionError("You do not have access to this course.")
    return course


def ensure_course_access_http(course_id: int, user: User, db: Session) -> Subject:
    """Same as ensure_course_access but raises HTTP 403 for FastAPI routes."""
    try:
        return ensure_course_access(course_id, user, db)
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.") from None


def is_course_instructor(user: User, course: Subject) -> bool:
    """Whether the user may manage course structure (e.g. material chapters). Admin always; else assigned teacher."""
    if user.role == UserRole.ADMIN:
        return True
    if user.role not in (UserRole.TEACHER, UserRole.CLASS_TEACHER):
        return False
    return course.teacher_id is not None and int(course.teacher_id) == int(user.id)


def sync_course_enrollments(course: Subject, db: Session) -> int:
    if not course.class_id:
        return 0
    if (course.course_type or "required").strip().lower() == "elective":
        # Electives are joined by student self-enrollment (or explicit roster picks), not whole-class auto sync.
        return 0

    class_students = db.query(Student).filter(Student.class_id == course.class_id).all()
    existing_student_ids = {
        enrollment.student_id
        for enrollment in db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == course.id).all()
    }

    created = 0
    for student in class_students:
        if student.id in existing_student_ids:
            continue
        try:
            with db.begin_nested():
                db.query(CourseEnrollmentBlock).filter(
                    CourseEnrollmentBlock.subject_id == course.id,
                    CourseEnrollmentBlock.student_id == student.id,
                ).delete(synchronize_session=False)
                db.add(
                    CourseEnrollment(
                        subject_id=course.id,
                        student_id=student.id,
                        class_id=course.class_id,
                        enrollment_type=course.course_type or "required",
                        can_remove=(course.course_type or "required") == "elective",
                    )
                )
                db.flush()
        except IntegrityError:
            enrollment_row = (
                db.query(CourseEnrollment)
                .filter(
                    CourseEnrollment.subject_id == course.id,
                    CourseEnrollment.student_id == student.id,
                )
                .first()
            )
            if enrollment_row:
                existing_student_ids.add(student.id)
            continue
        existing_student_ids.add(student.id)
        created += 1

    return created


def sync_student_course_enrollments(
    student: Student, db: Session, *, respect_enrollment_blocks: bool = True
) -> int:
    if not student.class_id:
        return 0

    courses = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    existing_course_ids = {
        enrollment.subject_id
        for enrollment in db.query(CourseEnrollment).filter(CourseEnrollment.student_id == student.id).all()
    }
    existing_course_ids.update(_pending_course_enrollment_subject_ids(db, student.id))

    blocked_subject_ids: set[int] = set()
    if respect_enrollment_blocks:
        blocked_subject_ids = {
            row[0]
            for row in db.query(CourseEnrollmentBlock.subject_id).filter(
                CourseEnrollmentBlock.student_id == student.id
            )
        }

    created = 0
    for course in courses:
        if (course.course_type or "required").strip().lower() == "elective":
            continue
        if course.id in existing_course_ids:
            continue
        if course.id in blocked_subject_ids:
            continue
        try:
            with db.begin_nested():
                db.add(
                    CourseEnrollment(
                        subject_id=course.id,
                        student_id=student.id,
                        class_id=student.class_id,
                        enrollment_type=course.course_type or "required",
                        can_remove=(course.course_type or "required") == "elective",
                    )
                )
                db.flush()
        except IntegrityError:
            existing_course_ids.add(course.id)
            continue
        existing_course_ids.add(course.id)
        created += 1

    return created


def remove_course_enrollment(course_id: int, student_id: int, db: Session) -> bool:
    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.subject_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
        .first()
    )
    if not enrollment:
        return False

    db.delete(enrollment)
    if not db.query(CourseEnrollmentBlock).filter(
        CourseEnrollmentBlock.subject_id == course_id,
        CourseEnrollmentBlock.student_id == student_id,
    ).first():
        db.add(CourseEnrollmentBlock(subject_id=course_id, student_id=student_id))
    return True


def get_enrolled_students(course_id: int, db: Session) -> list[CourseEnrollment]:
    return (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.subject_id == course_id)
        .options(joinedload(CourseEnrollment.student))
        .order_by(CourseEnrollment.id.asc())
        .all()
    )
