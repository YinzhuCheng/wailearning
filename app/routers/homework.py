import io
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.attachments import delete_attachment_file, get_attachment_file_path
from app.auth import get_current_active_user
from app.course_access import ensure_course_access, get_enrolled_students
from app.database import get_db
from app.models import Class, CourseEnrollment, Homework, HomeworkSubmission, Student, Subject, User, UserRole
from app.routers.classes import get_accessible_class_ids
from app.schemas import (
    HomeworkCreate,
    HomeworkListResponse,
    HomeworkResponse,
    HomeworkSubmissionCreate,
    HomeworkSubmissionDownloadRequest,
    HomeworkSubmissionResponse,
    HomeworkSubmissionStatusListResponse,
    HomeworkSubmissionStatusResponse,
    HomeworkUpdate,
)


router = APIRouter(prefix="/api/homeworks", tags=["作业管理"])


def is_teacher(user: User) -> bool:
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]


def _get_homework_or_404(homework_id: int, db: Session) -> Homework:
    homework = db.query(Homework).filter(Homework.id == homework_id).first()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found.")
    return homework


def _ensure_homework_access(homework: Homework, current_user: User, db: Session) -> Homework:
    allowed_class_ids = get_accessible_class_ids(current_user, db)
    if current_user.role != UserRole.ADMIN and homework.class_id not in allowed_class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this homework.")

    if homework.subject_id:
        try:
            ensure_course_access(homework.subject_id, current_user, db)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

    return homework


def _serialize_submission(submission: HomeworkSubmission) -> HomeworkSubmissionResponse:
    return HomeworkSubmissionResponse(
        id=submission.id,
        homework_id=submission.homework_id,
        student_id=submission.student_id,
        subject_id=submission.subject_id,
        class_id=submission.class_id,
        content=submission.content,
        attachment_name=submission.attachment_name,
        attachment_url=submission.attachment_url,
        submitted_at=submission.submitted_at,
        updated_at=submission.updated_at,
        student_name=submission.student.name if submission.student else None,
        student_no=submission.student.student_no if submission.student else None,
    )


def _serialize_submission_status(
    enrollment: Optional[CourseEnrollment],
    submission: Optional[HomeworkSubmission],
    fallback_student: Optional[Student] = None,
) -> HomeworkSubmissionStatusResponse:
    student = enrollment.student if enrollment and enrollment.student else fallback_student
    class_obj = enrollment.class_obj if enrollment and enrollment.class_obj else (student.class_obj if student else None)
    return HomeworkSubmissionStatusResponse(
        student_id=student.id if student else submission.student_id,
        student_name=student.name if student else None,
        student_no=student.student_no if student else None,
        class_name=class_obj.name if class_obj else None,
        submission_id=submission.id if submission else None,
        status="submitted" if submission else "pending",
        submitted_at=submission.submitted_at if submission else None,
        content=submission.content if submission else None,
        attachment_name=submission.attachment_name if submission else None,
        attachment_url=submission.attachment_url if submission else None,
    )


def _resolve_student_for_user(homework: Homework, current_user: User, db: Session) -> Student:
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit homework.")

    student_query = db.query(Student).filter(Student.class_id == homework.class_id)

    student = None
    if current_user.username:
        student = student_query.filter(Student.student_no == current_user.username).first()

    if not student and current_user.real_name:
        matches = student_query.filter(Student.name == current_user.real_name).all()
        if len(matches) == 1:
            student = matches[0]
        elif len(matches) > 1:
            raise HTTPException(
                status_code=400,
                detail="Multiple student records match the current account. Please contact an administrator.",
            )

    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found for the current account.")

    if homework.subject_id:
        enrollment = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.subject_id == homework.subject_id,
                CourseEnrollment.student_id == student.id,
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(status_code=403, detail="You are not enrolled in this course.")

    return student


def _is_homework_submission_closed(homework: Homework) -> bool:
    if not homework.due_date:
        return False

    current_time = datetime.now(homework.due_date.tzinfo) if homework.due_date.tzinfo else datetime.now()
    return current_time > homework.due_date


def _ensure_homework_submission_open(
    homework: Homework,
    payload: HomeworkSubmissionCreate,
    submission: Optional[HomeworkSubmission] = None,
) -> None:
    if not _is_homework_submission_closed(homework):
        return

    if payload.attachment_url and (not submission or payload.attachment_url != submission.attachment_url):
        delete_attachment_file(payload.attachment_url)

    raise HTTPException(status_code=400, detail="已超过作业截止时间，不能再提交或修改。")


def _serialize_homework(homework: Homework) -> HomeworkResponse:
    return HomeworkResponse(
        id=homework.id,
        title=homework.title,
        content=homework.content,
        attachment_name=homework.attachment_name,
        attachment_url=homework.attachment_url,
        class_id=homework.class_id,
        subject_id=homework.subject_id,
        due_date=homework.due_date,
        created_by=homework.created_by,
        created_at=homework.created_at,
        updated_at=homework.updated_at,
        class_name=homework.class_obj.name if homework.class_obj else None,
        subject_name=homework.subject.name if homework.subject else None,
        creator_name=homework.creator.real_name if homework.creator else None,
    )


@router.get("", response_model=HomeworkListResponse)
def get_homeworks(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(Homework)
    allowed_class_ids = get_accessible_class_ids(current_user, db)

    if current_user.role != UserRole.ADMIN:
        if not allowed_class_ids:
            return HomeworkListResponse(total=0, data=[])
        query = query.filter(Homework.class_id.in_(allowed_class_ids))

    if class_id:
        if current_user.role != UserRole.ADMIN and class_id not in allowed_class_ids:
            return HomeworkListResponse(total=0, data=[])
        query = query.filter(Homework.class_id == class_id)

    if subject_id:
        ensure_course_access(subject_id, current_user, db)
        query = query.filter(Homework.subject_id == subject_id)

    total = query.count()
    homeworks = query.order_by(desc(Homework.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return HomeworkListResponse(total=total, data=[_serialize_homework(homework) for homework in homeworks])


@router.get("/{homework_id}", response_model=HomeworkResponse)
def get_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    return _serialize_homework(homework)


@router.post("", response_model=HomeworkResponse)
def create_homework(
    data: HomeworkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can create homework.")

    allowed_class_ids = get_accessible_class_ids(current_user, db)
    if current_user.role != UserRole.ADMIN and data.class_id not in allowed_class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this class.")

    class_obj = db.query(Class).filter(Class.id == data.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found.")

    if data.subject_id:
        course = ensure_course_access(data.subject_id, current_user, db)
        if course.class_id and course.class_id != data.class_id:
            raise HTTPException(status_code=400, detail="The selected course does not belong to this class.")

    homework = Homework(
        title=data.title,
        content=data.content,
        attachment_name=data.attachment_name,
        attachment_url=data.attachment_url,
        class_id=data.class_id,
        subject_id=data.subject_id,
        due_date=data.due_date,
        created_by=current_user.id,
    )
    db.add(homework)
    db.commit()
    db.refresh(homework)
    return _serialize_homework(homework)


@router.put("/{homework_id}", response_model=HomeworkResponse)
def update_homework(
    homework_id: int,
    data: HomeworkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can update homework.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)

    if data.subject_id is not None:
        course = ensure_course_access(data.subject_id, current_user, db)
        if course.class_id and course.class_id != homework.class_id:
            raise HTTPException(status_code=400, detail="The selected course does not belong to this class.")

    if data.title is not None:
        homework.title = data.title
    if data.content is not None:
        homework.content = data.content
    if data.remove_attachment:
        delete_attachment_file(homework.attachment_url)
        homework.attachment_name = None
        homework.attachment_url = None
    elif data.attachment_url is not None:
        if homework.attachment_url and homework.attachment_url != data.attachment_url:
            delete_attachment_file(homework.attachment_url)
        homework.attachment_name = data.attachment_name
        homework.attachment_url = data.attachment_url
    if data.subject_id is not None:
        homework.subject_id = data.subject_id
    if data.due_date is not None:
        homework.due_date = data.due_date

    db.commit()
    db.refresh(homework)
    return _serialize_homework(homework)


@router.delete("/{homework_id}")
def delete_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can delete homework.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)

    for submission in list(homework.submissions):
        delete_attachment_file(submission.attachment_url)
        db.delete(submission)
    delete_attachment_file(homework.attachment_url)
    db.delete(homework)
    db.commit()
    return {"message": "Homework deleted successfully."}


@router.get("/{homework_id}/submission/me", response_model=Optional[HomeworkSubmissionResponse])
def get_my_homework_submission(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    student = _resolve_student_for_user(homework, current_user, db)
    submission = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework.id,
            HomeworkSubmission.student_id == student.id,
        )
        .first()
    )
    if not submission:
        return None
    return _serialize_submission(submission)


@router.post("/{homework_id}/submission", response_model=HomeworkSubmissionResponse)
def submit_homework(
    homework_id: int,
    data: HomeworkSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    student = _resolve_student_for_user(homework, current_user, db)

    submission = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework.id,
            HomeworkSubmission.student_id == student.id,
        )
        .first()
    )

    _ensure_homework_submission_open(homework, data, submission)

    if submission is None:
        submission = HomeworkSubmission(
            homework_id=homework.id,
            student_id=student.id,
            subject_id=homework.subject_id,
            class_id=homework.class_id,
        )
        db.add(submission)

    next_content = data.content
    next_attachment_name = submission.attachment_name if submission.attachment_name else None
    next_attachment_url = submission.attachment_url if submission.attachment_url else None

    if data.remove_attachment and submission.attachment_url:
        delete_attachment_file(submission.attachment_url)
        next_attachment_name = None
        next_attachment_url = None

    if data.attachment_url is not None:
        if submission.attachment_url and submission.attachment_url != data.attachment_url:
            delete_attachment_file(submission.attachment_url)
        next_attachment_name = data.attachment_name
        next_attachment_url = data.attachment_url

    if not (next_content or next_attachment_url):
        raise HTTPException(status_code=400, detail="Please provide submission content or an attachment.")

    submission.content = next_content
    submission.attachment_name = next_attachment_name
    submission.attachment_url = next_attachment_url

    db.commit()
    db.refresh(submission)
    return _serialize_submission(submission)


@router.get("/{homework_id}/submissions", response_model=HomeworkSubmissionStatusListResponse)
def get_homework_submissions(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can view homework submissions.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    submissions = (
        db.query(HomeworkSubmission)
        .filter(HomeworkSubmission.homework_id == homework.id)
        .order_by(HomeworkSubmission.submitted_at.desc())
        .all()
    )
    submission_map = {submission.student_id: submission for submission in submissions}

    rows: list[HomeworkSubmissionStatusResponse] = []
    if homework.subject_id:
        enrollments = get_enrolled_students(homework.subject_id, db)
        for enrollment in enrollments:
            rows.append(_serialize_submission_status(enrollment, submission_map.get(enrollment.student_id)))
    else:
        students = db.query(Student).filter(Student.class_id == homework.class_id).order_by(Student.id.asc()).all()
        for student in students:
            rows.append(_serialize_submission_status(None, submission_map.get(student.id), student))

    return HomeworkSubmissionStatusListResponse(total=len(rows), data=rows)


@router.post("/{homework_id}/submissions/download")
def download_homework_submissions(
    homework_id: int,
    payload: HomeworkSubmissionDownloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can download homework submissions.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)

    if not payload.submission_ids:
        raise HTTPException(status_code=400, detail="Please select at least one submission.")

    submissions = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework.id,
            HomeworkSubmission.id.in_(payload.submission_ids),
        )
        .order_by(HomeworkSubmission.submitted_at.asc())
        .all()
    )

    if not submissions:
        raise HTTPException(status_code=404, detail="No homework submissions found.")

    archive_buffer = io.BytesIO()
    added_files = 0
    used_names: set[str] = set()

    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for submission in submissions:
            file_path = get_attachment_file_path(submission.attachment_url)
            if not file_path or not file_path.exists():
                continue

            original_name = Path(submission.attachment_name or file_path.name).name
            student_account_id = (
                submission.student.student_no
                if submission.student and submission.student.student_no
                else str(submission.student_id)
            )
            safe_account_id = student_account_id.replace("/", "-").replace("\\", "-").strip() or str(submission.student_id)
            suffix = Path(original_name).suffix or file_path.suffix
            archive_name = f"{safe_account_id}{suffix}"
            counter = 1
            while archive_name in used_names:
                archive_name = f"{safe_account_id}-{counter}{suffix}"
                counter += 1

            archive.write(file_path, archive_name)
            used_names.add(archive_name)
            added_files += 1

    if not added_files:
        raise HTTPException(status_code=400, detail="The selected submissions do not contain downloadable attachments.")

    archive_buffer.seek(0)
    filename = f"{datetime.now().date().isoformat()}.zip"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
    }
    return StreamingResponse(archive_buffer, media_type="application/zip", headers=headers)
