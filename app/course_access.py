from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models import Class, CourseEnrollment, Student, Subject, User, UserRole


def get_accessible_courses_query(user: User, db: Session):
    query = db.query(Subject)

    if user.role == UserRole.ADMIN:
        return query

    if user.role == UserRole.STUDENT:
        if not user.class_id:
            return query.filter(False)
        return query.filter(Subject.class_id == user.class_id)

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


def get_accessible_course_ids(user: User, db: Session) -> list[int]:
    return [course.id for course in get_accessible_courses_query(user, db).all() if course.id]


def get_accessible_class_ids_from_courses(user: User, db: Session) -> list[int]:
    if user.role == UserRole.ADMIN:
        return [class_obj.id for class_obj in db.query(Class).all()]

    class_ids = set()
    if user.role == UserRole.CLASS_TEACHER and user.class_id:
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


def sync_course_enrollments(course: Subject, db: Session) -> int:
    if not course.class_id:
        return 0

    # Elective courses: enrollments are opt-in (roster API / seed), not whole-class auto-sync.
    if (course.course_type or "required") == "elective":
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
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=student.id,
                class_id=course.class_id,
                enrollment_type=course.course_type or "required",
                can_remove=(course.course_type or "required") == "elective",
            )
        )
        created += 1

    return created


def sync_student_course_enrollments(student: Student, db: Session) -> int:
    if not student.class_id:
        return 0

    courses = db.query(Subject).filter(Subject.class_id == student.class_id).all()
    existing_course_ids = {
        enrollment.subject_id
        for enrollment in db.query(CourseEnrollment).filter(CourseEnrollment.student_id == student.id).all()
    }

    created = 0
    for course in courses:
        if (course.course_type or "required") == "elective":
            continue
        if course.id in existing_course_ids:
            continue
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=student.id,
                class_id=student.class_id,
                enrollment_type=course.course_type or "required",
                can_remove=(course.course_type or "required") == "elective",
            )
        )
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
    return True


def get_enrolled_students(course_id: int, db: Session) -> list[CourseEnrollment]:
    return (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.subject_id == course_id)
        .order_by(CourseEnrollment.id.asc())
        .all()
    )
