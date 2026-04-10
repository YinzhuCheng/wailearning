from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.course_access import (
    ensure_course_access,
    get_accessible_courses_query,
    get_enrolled_students,
    remove_course_enrollment,
    sync_course_enrollments,
)
from app.database import get_db
from app.models import Class, CourseEnrollment, Semester, Student, Subject, User, UserRole
from app.schemas import (
    CourseEnrollmentResponse,
    CourseEnrollmentTypeUpdate,
    CourseRosterStudentInput,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
)


router = APIRouter(prefix="/api/subjects", tags=["课程管理"])


def _normalize_semester_label(semester: Optional[str], db: Session) -> Optional[str]:
    if not semester:
        return semester

    normalized = semester.strip()
    if not normalized:
        return normalized

    exact_semester = db.query(Semester).filter(Semester.name == normalized).first()
    if exact_semester:
        return exact_semester.name

    parts = normalized.split("-")
    if len(parts) == 2 and parts[0].isdigit():
        year, term = parts
        if term in {"1", "2"}:
            candidates = (
                db.query(Semester)
                .filter(Semester.year == int(year))
                .order_by(Semester.created_at.asc(), Semester.id.asc())
                .all()
            )
            term_index = int(term) - 1
            if 0 <= term_index < len(candidates):
                return candidates[term_index].name
        if term == "1":
            return f"{year}-春季"
        if term == "2":
            return f"{year}-秋季"

    return normalized


def _serialize_course(course: Subject, db: Session) -> SubjectResponse:
    student_count = db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == course.id).count()
    return SubjectResponse(
        id=course.id,
        name=course.name,
        teacher_id=course.teacher_id,
        class_id=course.class_id,
        course_type=course.course_type or "required",
        status=course.status or "active",
        semester=_normalize_semester_label(course.semester, db),
        weekly_schedule=course.weekly_schedule,
        course_start_at=course.course_start_at,
        course_end_at=course.course_end_at,
        description=course.description,
        teacher_name=course.teacher.real_name if course.teacher else None,
        class_name=course.class_obj.name if course.class_obj else None,
        student_count=student_count,
        created_at=course.created_at,
    )


def _serialize_enrollment(enrollment: CourseEnrollment) -> CourseEnrollmentResponse:
    enrollment_type = enrollment.enrollment_type or ("elective" if enrollment.can_remove else "required")
    return CourseEnrollmentResponse(
        id=enrollment.id,
        subject_id=enrollment.subject_id,
        student_id=enrollment.student_id,
        class_id=enrollment.class_id,
        enrollment_type=enrollment_type,
        can_remove=enrollment_type == "elective",
        created_at=enrollment.created_at,
        student_name=enrollment.student.name if enrollment.student else None,
        student_no=enrollment.student.student_no if enrollment.student else None,
        class_name=enrollment.class_obj.name if enrollment.class_obj else None,
    )


def _can_create_course(current_user: User) -> bool:
    return current_user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]


def _normalize_course_class_name(subject_data: SubjectCreate) -> str:
    if subject_data.class_name and subject_data.class_name.strip():
        return subject_data.class_name.strip()
    return f"{subject_data.name.strip()}课程班"


def _create_roster_students(
    course: Subject,
    students: List[CourseRosterStudentInput],
    db: Session,
    current_user: User,
) -> list[tuple[Student, str]]:
    seen_student_nos = set()
    enrollment_overrides: list[tuple[Student, str]] = []
    for item in students:
        student_name = item.name.strip()
        student_no = item.student_no.strip()
        if not student_name:
            raise HTTPException(status_code=400, detail="Student name is required.")
        if not student_no:
            raise HTTPException(status_code=400, detail="Student number is required.")
        if student_no in seen_student_nos:
            raise HTTPException(status_code=400, detail=f"Duplicate student number in upload: {student_no}")
        seen_student_nos.add(student_no)

        existing_student = (
            db.query(Student)
            .filter(Student.class_id == course.class_id, Student.student_no == student_no)
            .first()
        )
        if existing_student:
            raise HTTPException(status_code=400, detail=f"Student number already exists in this course roster: {student_no}")

        student = Student(
            name=student_name,
            student_no=student_no,
            gender=item.gender,
            phone=item.phone,
            parent_phone=item.parent_phone,
            address=item.address,
            class_id=course.class_id,
            teacher_id=current_user.id if current_user.role == UserRole.TEACHER.value else course.teacher_id,
        )
        db.add(student)
        enrollment_overrides.append((student, item.enrollment_type or "required"))

    return enrollment_overrides


@router.get("", response_model=List[SubjectResponse])
def get_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    courses = (
        get_accessible_courses_query(current_user, db)
        .order_by(Subject.status.asc(), Subject.created_at.desc())
        .all()
    )
    return [_serialize_course(course, db) for course in courses]


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        course = ensure_course_access(subject_id, current_user, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.")

    return _serialize_course(course, db)


@router.post("", response_model=SubjectResponse)
def create_subject(
    subject_data: SubjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _can_create_course(current_user):
        raise HTTPException(status_code=403, detail="You do not have permission to create courses.")

    if subject_data.course_end_at and subject_data.course_start_at and subject_data.course_end_at < subject_data.course_start_at:
        raise HTTPException(status_code=400, detail="Course end time must be later than start time.")

    target_teacher_id: Optional[int] = subject_data.teacher_id
    if current_user.role != UserRole.ADMIN:
        target_teacher_id = current_user.id

    class_obj = None
    if subject_data.class_id is not None:
        class_obj = db.query(Class).filter(Class.id == subject_data.class_id).first()
        if not class_obj:
            raise HTTPException(status_code=400, detail="Class not found.")

    if class_obj is None:
        if not subject_data.students:
            raise HTTPException(status_code=400, detail="Please upload a student roster or choose an existing class.")
        class_obj = Class(name=_normalize_course_class_name(subject_data), grade=1)
        db.add(class_obj)
        db.flush()

    existing = (
        db.query(Subject)
        .filter(
            Subject.name == subject_data.name,
            Subject.class_id == class_obj.id,
            Subject.semester == subject_data.semester,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="A course with the same name already exists for this class and semester.")

    course = Subject(
        name=subject_data.name,
        teacher_id=target_teacher_id,
        class_id=class_obj.id,
        course_type=subject_data.course_type,
        status=subject_data.status,
        semester=subject_data.semester,
        weekly_schedule=subject_data.weekly_schedule,
        course_start_at=subject_data.course_start_at,
        course_end_at=subject_data.course_end_at,
        description=subject_data.description,
    )
    db.add(course)
    db.flush()

    enrollment_overrides: list[tuple[Student, str]] = []
    if subject_data.students:
        enrollment_overrides = _create_roster_students(course, subject_data.students, db, current_user)
        db.flush()

    sync_course_enrollments(course, db)
    if enrollment_overrides:
        db.flush()
        for student, enrollment_type in enrollment_overrides:
            if not student.id:
                continue
            enrollment = (
                db.query(CourseEnrollment)
                .filter(
                    CourseEnrollment.subject_id == course.id,
                    CourseEnrollment.student_id == student.id,
                )
                .first()
            )
            if enrollment:
                normalized_enrollment_type = enrollment_type.strip().lower()
                enrollment.enrollment_type = normalized_enrollment_type
                enrollment.can_remove = normalized_enrollment_type == "elective"
    db.commit()
    db.refresh(course)
    return _serialize_course(course, db)


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: int,
    subject_data: SubjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.ADMIN:
        pass
    else:
        try:
            ensure_course_access(subject_id, current_user, db)
        except ValueError:
            raise HTTPException(status_code=404, detail="Course not found.")
        except PermissionError:
            raise HTTPException(status_code=403, detail="You do not have access to this course.")

    course = db.query(Subject).filter(Subject.id == subject_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    original_class_id = course.class_id

    if subject_data.course_end_at and subject_data.course_start_at and subject_data.course_end_at < subject_data.course_start_at:
        raise HTTPException(status_code=400, detail="Course end time must be later than start time.")

    if current_user.role != UserRole.ADMIN and subject_data.teacher_id is not None and subject_data.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only assign yourself as the course teacher.")

    if current_user.role != UserRole.ADMIN:
        subject_data.teacher_id = current_user.id

    for field in ["name", "teacher_id", "class_id", "course_type", "status", "semester", "weekly_schedule", "course_start_at", "course_end_at", "description"]:
        value = getattr(subject_data, field)
        if value is not None:
            setattr(course, field, value)

    if course.class_id is None:
        raise HTTPException(status_code=400, detail="Course must belong to a class.")

    if course.class_id != original_class_id:
        db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == course.id).delete()

    sync_course_enrollments(course, db)
    db.commit()
    db.refresh(course)
    return _serialize_course(course, db)


@router.delete("/{subject_id}")
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.ADMIN:
        pass
    else:
        try:
            ensure_course_access(subject_id, current_user, db)
        except ValueError:
            raise HTTPException(status_code=404, detail="Course not found.")
        except PermissionError:
            raise HTTPException(status_code=403, detail="You do not have access to this course.")

    course = db.query(Subject).filter(Subject.id == subject_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == subject_id).delete()
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully."}


@router.get("/{subject_id}/students", response_model=List[CourseEnrollmentResponse])
def get_subject_students(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        ensure_course_access(subject_id, current_user, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.")

    enrollments = get_enrolled_students(subject_id, db)
    return [_serialize_enrollment(enrollment) for enrollment in enrollments]


@router.put("/{subject_id}/students/{student_id}/enrollment-type", response_model=CourseEnrollmentResponse)
def update_subject_student_enrollment_type(
    subject_id: int,
    student_id: int,
    payload: CourseEnrollmentTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students cannot modify course enrollment types.")

    try:
        ensure_course_access(subject_id, current_user, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.")

    enrollment_type = payload.enrollment_type.strip().lower()
    if enrollment_type not in {"required", "elective"}:
        raise HTTPException(status_code=400, detail="Enrollment type must be required or elective.")

    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.subject_id == subject_id,
            CourseEnrollment.student_id == student_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(status_code=404, detail="Course student not found.")

    enrollment.enrollment_type = enrollment_type
    enrollment.can_remove = enrollment_type == "elective"
    db.commit()
    db.refresh(enrollment)
    return _serialize_enrollment(enrollment)


@router.delete("/{subject_id}/students/{student_id}")
def remove_subject_student(
    subject_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students cannot modify course rosters.")

    try:
        ensure_course_access(subject_id, current_user, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.")

    removed = remove_course_enrollment(subject_id, student_id, db)
    if not removed:
        raise HTTPException(status_code=404, detail="Course student not found.")

    db.commit()
    return {"message": "Student removed from course successfully."}
