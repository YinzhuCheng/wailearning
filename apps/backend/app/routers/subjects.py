import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.course_access import (
    ensure_course_access,
    get_accessible_courses_query,
    get_enrolled_students,
    get_student_course_catalog_query,
    get_student_elective_catalog_query,
    get_student_profile_for_user,
    prepare_student_course_context,
    remove_course_enrollment,
    sync_course_enrollments,
)
from app.database import get_db
from app.models import Class, CourseEnrollment, CourseEnrollmentBlock, Semester, Student, Subject, User, UserRole
from app.schemas import (
    CourseTimeItem,
    CourseEnrollmentResponse,
    CourseEnrollmentTypeUpdate,
    CourseRosterStudentInput,
    StudentCourseCatalogItem,
    StudentElectiveSelfDropResult,
    StudentElectiveSelfEnrollResult,
    SubjectCreate,
    SubjectResponse,
    SubjectUpdate,
    SubjectRosterEnrollRequest,
    SubjectRosterEnrollResult,
)


router = APIRouter(prefix="/api/subjects", tags=["课程管理"])


def _sort_course_times(course_times: List[CourseTimeItem]) -> List[CourseTimeItem]:
    return sorted(
        course_times,
        key=lambda item: (item.course_start_at, item.course_end_at, item.weekly_schedule or ""),
    )


def _build_legacy_course_times(
    weekly_schedule: Optional[str],
    course_start_at,
    course_end_at,
) -> List[CourseTimeItem]:
    if not weekly_schedule or not course_start_at or not course_end_at:
        return []

    return [
        CourseTimeItem(
            weekly_schedule=weekly_schedule,
            course_start_at=course_start_at,
            course_end_at=course_end_at,
        )
    ]


def _resolve_course_times(
    course_times: Optional[List[CourseTimeItem]],
    weekly_schedule: Optional[str],
    course_start_at,
    course_end_at,
) -> List[CourseTimeItem]:
    normalized = [CourseTimeItem.model_validate(item) for item in (course_times or [])]

    if not normalized:
        normalized = _build_legacy_course_times(
            weekly_schedule=weekly_schedule,
            course_start_at=course_start_at,
            course_end_at=course_end_at,
        )

    return _sort_course_times(normalized)


def _deserialize_course_times(course: Subject) -> List[CourseTimeItem]:
    if course.course_times:
        try:
            raw_items = json.loads(course.course_times)
            normalized_items = []

            for raw_item in raw_items or []:
                try:
                    normalized_items.append(CourseTimeItem.model_validate(raw_item))
                except Exception:
                    continue

            if normalized_items:
                return _sort_course_times(normalized_items)
        except Exception:
            pass

    return _build_legacy_course_times(
        weekly_schedule=course.weekly_schedule,
        course_start_at=course.course_start_at,
        course_end_at=course.course_end_at,
    )


def _serialize_course_times_for_storage(course_times: List[CourseTimeItem]) -> Optional[str]:
    if not course_times:
        return None

    return json.dumps(
        [
            {
                "weekly_schedule": item.weekly_schedule,
                "course_start_at": item.course_start_at.isoformat(),
                "course_end_at": item.course_end_at.isoformat(),
            }
            for item in course_times
        ],
        ensure_ascii=False,
    )


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
            return f"{year}-\u6625\u5b63"
        if term == "2":
            return f"{year}-\u79cb\u5b63"
        if term == "1":
            return f"{year}-春季"
        if term == "2":
            return f"{year}-秋季"

    return normalized


def _resolve_semester(
    db: Session,
    *,
    semester_id: Optional[int] = None,
    semester_name: Optional[str] = None,
) -> Optional[Semester]:
    if semester_id:
        semester = db.query(Semester).filter(Semester.id == semester_id).first()
        if not semester:
            raise HTTPException(status_code=400, detail="Semester not found.")
        return semester

    normalized_name = _normalize_semester_label(semester_name, db)
    if not normalized_name:
        return None

    semester = db.query(Semester).filter(Semester.name == normalized_name).first()
    if semester:
        return semester

    raise HTTPException(status_code=400, detail="Semester not found.")


def _serialize_course(course: Subject, db: Session) -> SubjectResponse:
    student_count = db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == course.id).count()
    semester_label = (
        course.semester_obj.name
        if course.semester_obj
        else _normalize_semester_label(course.semester, db)
    )
    course_times = _deserialize_course_times(course)
    primary_course_time = course_times[0] if course_times else None
    return SubjectResponse(
        id=course.id,
        name=course.name,
        teacher_id=course.teacher_id,
        class_id=course.class_id,
        semester_id=course.semester_id,
        course_type=course.course_type or "required",
        status=course.status or "active",
        semester=semester_label,
        weekly_schedule=primary_course_time.weekly_schedule if primary_course_time else course.weekly_schedule,
        course_start_at=primary_course_time.course_start_at if primary_course_time else course.course_start_at,
        course_end_at=primary_course_time.course_end_at if primary_course_time else course.course_end_at,
        course_times=course_times,
        description=course.description,
        teacher_name=course.teacher.real_name if course.teacher else None,
        class_name=course.class_obj.name if course.class_obj else None,
        student_count=student_count,
        created_at=course.created_at,
    )


def _serialize_student_course_catalog_item(
    course: Subject,
    db: Session,
    *,
    student: Student,
    enrolled_subject_ids: set[int],
) -> StudentCourseCatalogItem:
    base = _serialize_course(course, db)
    ct = (course.course_type or "required").strip().lower()
    is_enrolled = course.id in enrolled_subject_ids
    same_class = (
        course.class_id is not None
        and student.class_id is not None
        and int(course.class_id) == int(student.class_id)
    )
    if ct == "elective":
        if is_enrolled:
            hint = "已选修，可退选。"
        elif not course.class_id:
            hint = "课程未绑定班级，暂不可选课。"
        elif not same_class:
            hint = "仅可选修本班开设的课程；其他班级课程可浏览，选课按钮不可用。"
        else:
            hint = "本班开设的选修课，可自行选课。"
        can_self = bool(same_class and course.class_id and not is_enrolled)
    else:
        if is_enrolled:
            hint = "已在花名册中（通常由教师按班级统一添加）。"
        else:
            hint = "必修课由教师按班级花名册统一加入，不可在此自主选课；若应修而未显示请联系任课教师或管理员。"
        can_self = False
    return StudentCourseCatalogItem(
        **base.model_dump(),
        is_enrolled=is_enrolled,
        enrollment_hint=hint,
        can_self_enroll_elective=can_self,
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


@router.get("/course-catalog", response_model=List[StudentCourseCatalogItem])
def list_student_course_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Active courses schoolwide for students: 必修/选修 labels + enrollment conditions; electives self-enroll only same class."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can browse the course catalog.")

    prepare_student_course_context(current_user, db)
    db.commit()
    student = get_student_profile_for_user(current_user, db)
    if not student:
        raise HTTPException(status_code=400, detail="未找到与账号匹配的花名册，无法浏览选课目录。")

    enrolled_ids = {
        row[0]
        for row in db.query(CourseEnrollment.subject_id)
        .filter(CourseEnrollment.student_id == student.id)
        .all()
    }
    courses = get_student_course_catalog_query(current_user, db).order_by(Subject.created_at.desc()).all()
    return [_serialize_student_course_catalog_item(c, db, student=student, enrolled_subject_ids=enrolled_ids) for c in courses]


@router.get("/elective-catalog", response_model=List[SubjectResponse])
def list_elective_catalog_for_student(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Active elective courses available for voluntary student self-enrollment."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can browse the elective catalog.")

    courses = (
        get_student_elective_catalog_query(current_user, db)
        .order_by(Subject.created_at.desc())
        .all()
    )
    return [_serialize_course(course, db) for course in courses]


@router.post("/{subject_id}/student-self-enroll", response_model=StudentElectiveSelfEnrollResult)
def student_self_enroll_elective(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can self-enroll.")

    prepare_student_course_context(current_user, db)
    db.commit()
    student = get_student_profile_for_user(current_user, db)
    if not student:
        raise HTTPException(status_code=400, detail="未找到与账号匹配的花名册，无法选课。")

    course = db.query(Subject).filter(Subject.id == subject_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")
    if (course.status or "").strip() != "active":
        raise HTTPException(status_code=400, detail="课程未开放选课。")
    if (course.course_type or "").strip() != "elective":
        raise HTTPException(status_code=400, detail="仅选修课支持学生自主选课。")
    if not course.class_id:
        raise HTTPException(status_code=400, detail="课程未绑定班级，无法选课。")

    if student.class_id != course.class_id:
        raise HTTPException(
            status_code=400,
            detail="只能选修所属行政班开设的选修课；如需调整班级请联系管理员。",
        )

    existing = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.subject_id == course.id, CourseEnrollment.student_id == student.id)
        .first()
    )
    if existing:
        return StudentElectiveSelfEnrollResult(subject_id=course.id, created=False, already_enrolled=True)

    try:
        db.query(CourseEnrollmentBlock).filter(
            CourseEnrollmentBlock.subject_id == course.id,
            CourseEnrollmentBlock.student_id == student.id,
        ).delete(synchronize_session=False)
        db.add(
            CourseEnrollment(
                subject_id=course.id,
                student_id=student.id,
                class_id=course.class_id,
                enrollment_type="elective",
                can_remove=True,
            )
        )
        db.commit()
        return StudentElectiveSelfEnrollResult(subject_id=course.id, created=True, already_enrolled=False)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.subject_id == course.id, CourseEnrollment.student_id == student.id)
            .first()
        )
        if existing:
            return StudentElectiveSelfEnrollResult(subject_id=course.id, created=False, already_enrolled=True)
        raise


@router.post("/{subject_id}/student-self-drop", response_model=StudentElectiveSelfDropResult)
def student_self_drop_elective(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can drop electives.")

    prepare_student_course_context(current_user, db)
    db.commit()
    student = get_student_profile_for_user(current_user, db)
    if not student:
        raise HTTPException(status_code=400, detail="未找到与账号匹配的花名册。")

    enrollment = (
        db.query(CourseEnrollment)
        .filter(CourseEnrollment.subject_id == subject_id, CourseEnrollment.student_id == student.id)
        .first()
    )
    if not enrollment:
        return StudentElectiveSelfDropResult(subject_id=subject_id, removed=False)

    et = (enrollment.enrollment_type or "").strip().lower()
    if et != "elective" and not enrollment.can_remove:
        raise HTTPException(status_code=400, detail="必修课不可退选。")

    try:
        db.delete(enrollment)
        if not db.query(CourseEnrollmentBlock).filter(
            CourseEnrollmentBlock.subject_id == subject_id,
            CourseEnrollmentBlock.student_id == student.id,
        ).first():
            db.add(CourseEnrollmentBlock(subject_id=subject_id, student_id=student.id))
        db.commit()
        return StudentElectiveSelfDropResult(subject_id=subject_id, removed=True)
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.subject_id == subject_id, CourseEnrollment.student_id == student.id)
            .first()
        )
        if not existing:
            return StudentElectiveSelfDropResult(subject_id=subject_id, removed=False)
        raise


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

    semester_obj = _resolve_semester(
        db,
        semester_id=subject_data.semester_id,
        semester_name=subject_data.semester,
    )
    semester_label = semester_obj.name if semester_obj else None
    course_times = _resolve_course_times(
        subject_data.course_times,
        subject_data.weekly_schedule,
        subject_data.course_start_at,
        subject_data.course_end_at,
    )
    primary_course_time = course_times[0] if course_times else None

    existing = (
        db.query(Subject)
        .filter(
            Subject.name == subject_data.name,
            Subject.class_id == class_obj.id,
            Subject.semester_id == (semester_obj.id if semester_obj else None),
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="A course with the same name already exists for this class and semester.")

    course = Subject(
        name=subject_data.name,
        teacher_id=target_teacher_id,
        class_id=class_obj.id,
        semester_id=semester_obj.id if semester_obj else None,
        course_type=subject_data.course_type,
        status=subject_data.status,
        semester=semester_label,
        weekly_schedule=primary_course_time.weekly_schedule if primary_course_time else subject_data.weekly_schedule,
        course_start_at=primary_course_time.course_start_at if primary_course_time else subject_data.course_start_at,
        course_end_at=primary_course_time.course_end_at if primary_course_time else subject_data.course_end_at,
        course_times=_serialize_course_times_for_storage(course_times),
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

    for field in ["name", "teacher_id", "class_id", "course_type", "status", "description"]:
        value = getattr(subject_data, field)
        if value is not None:
            setattr(course, field, value)

    if (
        subject_data.course_times is not None
        or subject_data.weekly_schedule is not None
        or subject_data.course_start_at is not None
        or subject_data.course_end_at is not None
    ):
        course_times = _resolve_course_times(
            subject_data.course_times,
            subject_data.weekly_schedule,
            subject_data.course_start_at,
            subject_data.course_end_at,
        )
        primary_course_time = course_times[0] if course_times else None
        course.course_times = _serialize_course_times_for_storage(course_times)
        course.weekly_schedule = primary_course_time.weekly_schedule if primary_course_time else None
        course.course_start_at = primary_course_time.course_start_at if primary_course_time else None
        course.course_end_at = primary_course_time.course_end_at if primary_course_time else None

    if subject_data.semester_id is not None or subject_data.semester is not None:
        semester_obj = _resolve_semester(
            db,
            semester_id=subject_data.semester_id,
            semester_name=subject_data.semester,
        )
        course.semester_id = semester_obj.id if semester_obj else None
        course.semester = semester_obj.name if semester_obj else None

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


@router.post("/{subject_id}/sync-enrollments")
def sync_subject_enrollments(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Reconcile course_enrollments with the course class roster (idempotent)."""
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students cannot modify course rosters.")

    try:
        course = ensure_course_access(subject_id, current_user, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.")

    created = sync_course_enrollments(course, db)
    db.commit()
    db.refresh(course)
    return {
        "message": "Course enrollments synchronized.",
        "created": created,
        "student_count": db.query(CourseEnrollment).filter(CourseEnrollment.subject_id == course.id).count(),
    }


@router.post("/{subject_id}/roster-enroll", response_model=SubjectRosterEnrollResult)
def enroll_roster_students_on_subject(
    subject_id: int,
    payload: SubjectRosterEnrollRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Add CourseEnrollment rows only for students who already belong to the course's class roster.
    Does not create Student rows or move students between classes — use roster / 调班 flows first.
    """
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students cannot modify course rosters.")

    try:
        course = ensure_course_access(subject_id, current_user, db)
    except ValueError:
        raise HTTPException(status_code=404, detail="Course not found.")
    except PermissionError:
        raise HTTPException(status_code=403, detail="You do not have access to this course.")

    if not course.class_id:
        raise HTTPException(status_code=400, detail="Course has no class; cannot roster-enroll.")

    student_ids = list(dict.fromkeys(payload.student_ids))
    if not student_ids:
        return SubjectRosterEnrollResult()

    enrolled_ids = {
        row[0]
        for row in db.query(CourseEnrollment.student_id).filter(CourseEnrollment.subject_id == course.id).all()
    }

    created = 0
    skipped_already = 0
    skipped_wrong_class = 0
    skipped_missing = 0
    enrollment_type = course.course_type or "required"
    can_remove = enrollment_type == "elective"

    for student_id in student_ids:
        if student_id in enrolled_ids:
            skipped_already += 1
            continue

        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            skipped_missing += 1
            continue

        if student.class_id != course.class_id:
            skipped_wrong_class += 1
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
                        enrollment_type=enrollment_type,
                        can_remove=can_remove,
                    )
                )
                db.flush()
            enrolled_ids.add(student.id)
            created += 1
        except IntegrityError:
            existing = (
                db.query(CourseEnrollment)
                .filter(
                    CourseEnrollment.subject_id == course.id,
                    CourseEnrollment.student_id == student.id,
                )
                .first()
            )
            if existing:
                skipped_already += 1
                continue
            raise

    db.commit()
    return SubjectRosterEnrollResult(
        created=created,
        skipped_already_enrolled=skipped_already,
        skipped_not_in_class_roster=skipped_wrong_class,
        skipped_not_found=skipped_missing,
    )


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
