import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session
from starlette.responses import StreamingResponse

from app.attachments import (
    delete_attachment_file,
    delete_attachment_file_if_unreferenced,
    get_attachment_file_path,
)
from app.auth import get_current_active_user
from app.course_access import ensure_course_access, get_enrolled_students
from app.database import get_db
from app.llm_grading import normalize_score_for_homework, queue_grading_task, refresh_submission_summary
from app.models import (
    Class,
    CourseEnrollment,
    Homework,
    HomeworkAttempt,
    HomeworkGradingTask,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMTokenUsageLog,
    Student,
    User,
    UserRole,
)
from app.routers.classes import get_accessible_class_ids
from app.schemas import (
    HomeworkAttemptResponse,
    HomeworkBatchLateSubmissionUpdate,
    HomeworkBatchRegradeItemResult,
    HomeworkBatchRegradeRequest,
    HomeworkBatchRegradeResponse,
    HomeworkCreate,
    HomeworkListResponse,
    HomeworkRegradeRequest,
    HomeworkResponse,
    HomeworkSubmissionCreate,
    HomeworkSubmissionDownloadRequest,
    HomeworkSubmissionHistoryResponse,
    HomeworkSubmissionReviewUpdate,
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


def _match_student_for_user(student_query, current_user: User) -> Optional[Student]:
    """Map login user -> Student by student_no (must match user.username)."""
    if not current_user.username:
        return None
    return student_query.filter(Student.student_no == current_user.username).first()


def _resolve_student_for_user(homework: Homework, current_user: User, db: Session) -> Student:
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit homework.")

    student_query = db.query(Student).filter(Student.class_id == homework.class_id)
    student = _match_student_for_user(student_query, current_user)
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


def _grade_rule_hint(homework: Homework) -> str:
    return f"多次提交取最高分；迟交默认{'影响' if homework.late_submission_affects_score else '不影响'}评分，系统会标记迟交。"


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
    if not _is_homework_submission_closed(homework) or homework.allow_late_submission:
        return

    if payload.attachment_url and (not submission or payload.attachment_url != submission.attachment_url):
        delete_attachment_file(payload.attachment_url)
    raise HTTPException(status_code=400, detail="已超过作业截止时间，不能再提交或修改。")


def _is_late_attempt(homework: Homework, submitted_at: datetime) -> bool:
    if not homework.due_date:
        return False
    due_date = homework.due_date
    if due_date.tzinfo and not submitted_at.tzinfo:
        submitted_at = submitted_at.replace(tzinfo=due_date.tzinfo)
    elif submitted_at.tzinfo and not due_date.tzinfo:
        due_date = due_date.replace(tzinfo=submitted_at.tzinfo)
    return submitted_at > due_date


def _counts_toward_final_score(homework: Homework, is_late: bool) -> bool:
    return (not is_late) or (not homework.late_submission_affects_score)


def _latest_task_for_attempt(db: Session, attempt_id: Optional[int]) -> Optional[HomeworkGradingTask]:
    if not attempt_id:
        return None
    return (
        db.query(HomeworkGradingTask)
        .filter(HomeworkGradingTask.attempt_id == attempt_id)
        .order_by(HomeworkGradingTask.created_at.desc(), HomeworkGradingTask.id.desc())
        .first()
    )


def _best_candidate_for_attempt(db: Session, attempt_id: int) -> Optional[HomeworkScoreCandidate]:
    candidates = (
        db.query(HomeworkScoreCandidate)
        .filter(HomeworkScoreCandidate.attempt_id == attempt_id)
        .order_by(HomeworkScoreCandidate.updated_at.desc(), HomeworkScoreCandidate.id.desc())
        .all()
    )
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (
            float(item.score or 0),
            1 if item.source == "teacher" else 0,
            item.updated_at or item.created_at,
        ),
    )


def _get_submission_summary(db: Session, homework_id: int, student_id: int) -> Optional[HomeworkSubmission]:
    return (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == student_id,
        )
        .first()
    )


def _serialize_submission(db: Session, submission: HomeworkSubmission) -> HomeworkSubmissionResponse:
    refresh_submission_summary(db, submission)
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
        review_score=submission.review_score,
        review_comment=submission.review_comment,
        latest_attempt_id=submission.latest_attempt_id,
        latest_task_status=submission.latest_task_status,
        latest_task_error=submission.latest_task_error,
    )


def _serialize_attempt(db: Session, attempt: HomeworkAttempt) -> HomeworkAttemptResponse:
    best_candidate = _best_candidate_for_attempt(db, attempt.id)
    task = _latest_task_for_attempt(db, attempt.id)
    return HomeworkAttemptResponse(
        id=attempt.id,
        homework_id=attempt.homework_id,
        student_id=attempt.student_id,
        subject_id=attempt.subject_id,
        class_id=attempt.class_id,
        submission_summary_id=attempt.submission_summary_id,
        content=attempt.content,
        attachment_name=attempt.attachment_name,
        attachment_url=attempt.attachment_url,
        is_late=bool(attempt.is_late),
        counts_toward_final_score=bool(attempt.counts_toward_final_score),
        submitted_at=attempt.submitted_at,
        updated_at=attempt.updated_at,
        review_score=best_candidate.score if best_candidate else None,
        review_comment=best_candidate.comment if best_candidate else None,
        task_status=task.status if task else None,
        task_error=task.error_message if task else None,
        score_source=best_candidate.source if best_candidate else None,
    )


def _serialize_history(db: Session, submission: Optional[HomeworkSubmission]) -> HomeworkSubmissionHistoryResponse:
    if not submission:
        return HomeworkSubmissionHistoryResponse(summary=None, attempts=[])
    refresh_submission_summary(db, submission)
    attempts = (
        db.query(HomeworkAttempt)
        .filter(HomeworkAttempt.submission_summary_id == submission.id)
        .order_by(HomeworkAttempt.submitted_at.desc(), HomeworkAttempt.id.desc())
        .all()
    )
    return HomeworkSubmissionHistoryResponse(
        summary=_serialize_submission(db, submission),
        attempts=[_serialize_attempt(db, attempt) for attempt in attempts],
    )


def _serialize_submission_status(
    db: Session,
    enrollment: Optional[CourseEnrollment],
    submission: Optional[HomeworkSubmission],
    fallback_student: Optional[Student] = None,
) -> HomeworkSubmissionStatusResponse:
    student = enrollment.student if enrollment and enrollment.student else fallback_student
    class_obj = enrollment.class_obj if enrollment and enrollment.class_obj else (student.class_obj if student else None)
    if submission:
        refresh_submission_summary(db, submission)
    latest_attempt = submission.latest_attempt if submission else None
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
        review_score=submission.review_score if submission else None,
        review_comment=submission.review_comment if submission else None,
        latest_attempt_id=submission.latest_attempt_id if submission else None,
        latest_attempt_is_late=latest_attempt.is_late if latest_attempt else None,
        latest_task_status=submission.latest_task_status if submission else None,
        latest_task_error=submission.latest_task_error if submission else None,
        attempt_count=len(submission.attempts) if submission else 0,
    )


def _serialize_homework(homework: Homework, submission: Optional[HomeworkSubmission] = None) -> HomeworkResponse:
    if submission:
        review_score = submission.review_score
        review_comment = submission.review_comment
        task_status = submission.latest_task_status
        task_error = submission.latest_task_error
        attempt_count = len(submission.attempts)
        latest_submission_is_late = submission.latest_attempt.is_late if submission.latest_attempt else None
    else:
        review_score = None
        review_comment = None
        task_status = None
        task_error = None
        attempt_count = 0
        latest_submission_is_late = None

    return HomeworkResponse(
        id=homework.id,
        title=homework.title,
        content=homework.content,
        attachment_name=homework.attachment_name,
        attachment_url=homework.attachment_url,
        class_id=homework.class_id,
        subject_id=homework.subject_id,
        due_date=homework.due_date,
        max_score=homework.max_score,
        grade_precision=homework.grade_precision,
        auto_grading_enabled=homework.auto_grading_enabled,
        rubric_text=homework.rubric_text,
        reference_answer=homework.reference_answer,
        response_language=homework.response_language,
        allow_late_submission=homework.allow_late_submission,
        late_submission_affects_score=homework.late_submission_affects_score,
        created_by=homework.created_by,
        created_at=homework.created_at,
        updated_at=homework.updated_at,
        class_name=homework.class_obj.name if homework.class_obj else None,
        subject_name=homework.subject.name if homework.subject else None,
        creator_name=homework.creator.real_name if homework.creator else None,
        review_score=review_score,
        review_comment=review_comment,
        task_status=task_status,
        task_error=task_error,
        attempt_count=attempt_count,
        latest_submission_is_late=latest_submission_is_late,
        grading_rule_hint=_grade_rule_hint(homework),
    )


def _serialize_homework_for_user(
    homework: Homework,
    current_user: User,
    submission: Optional[HomeworkSubmission] = None,
) -> HomeworkResponse:
    response = _serialize_homework(homework, submission)
    if current_user.role == UserRole.STUDENT:
        response.reference_answer = None
        response.rubric_text = None
    return response


def _resolve_target_attempt(db: Session, submission: HomeworkSubmission, attempt_id: Optional[int]) -> HomeworkAttempt:
    if attempt_id is not None:
        attempt = (
            db.query(HomeworkAttempt)
            .filter(
                HomeworkAttempt.id == attempt_id,
                HomeworkAttempt.submission_summary_id == submission.id,
            )
            .first()
        )
    else:
        attempt = submission.latest_attempt
    if not attempt:
        raise HTTPException(status_code=404, detail="Homework attempt not found.")
    return attempt


def _delete_attachment_if_unreferenced(
    db: Session,
    attachment_url: Optional[str],
    *,
    exclude_homework_id: Optional[int] = None,
    exclude_submission_id: Optional[int] = None,
    exclude_attempt_id: Optional[int] = None,
) -> None:
    from app.attachments import attachment_is_referenced

    if not attachment_url:
        return
    if attachment_is_referenced(db, attachment_url):
        return
    delete_attachment_file(attachment_url)


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

    submission_map: dict[int, HomeworkSubmission] = {}
    if current_user.role == UserRole.STUDENT and homeworks:
        class_ids = {item.class_id for item in homeworks}
        student = _match_student_for_user(db.query(Student).filter(Student.class_id.in_(class_ids)), current_user)
        if student:
            submission_rows = (
                db.query(HomeworkSubmission)
                .filter(
                    HomeworkSubmission.homework_id.in_([item.id for item in homeworks]),
                    HomeworkSubmission.student_id == student.id,
                )
                .all()
            )
            for row in submission_rows:
                refresh_submission_summary(db, row)
            submission_map = {row.homework_id: row for row in submission_rows}

    return HomeworkListResponse(
        total=total,
        data=[_serialize_homework_for_user(homework, current_user, submission_map.get(homework.id)) for homework in homeworks],
    )


@router.post("/batch-late-submission", response_model=dict)
def batch_update_late_submission_policy(
    payload: HomeworkBatchLateSubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """批量更新作业的「允许迟交」「迟交是否影响评分」。仅处理当前用户有权限的作业。"""
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can update homework.")

    allowed_class_ids = get_accessible_class_ids(current_user, db)
    if current_user.role != UserRole.ADMIN and not allowed_class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to any classes.")

    ids = list(dict.fromkeys(payload.homework_ids))
    rows = db.query(Homework).filter(Homework.id.in_(ids)).all()
    found = {h.id: h for h in rows}
    missing = [i for i in ids if i not in found]
    forbidden: list[int] = []
    updated = 0
    for hid in ids:
        hw = found.get(hid)
        if not hw:
            continue
        if current_user.role != UserRole.ADMIN and hw.class_id not in allowed_class_ids:
            forbidden.append(hid)
            continue
        if hw.subject_id:
            try:
                ensure_course_access(hw.subject_id, current_user, db)
            except ValueError:
                forbidden.append(hid)
                continue
            except PermissionError:
                forbidden.append(hid)
                continue
        if payload.allow_late_submission is not None:
            hw.allow_late_submission = payload.allow_late_submission
        if payload.late_submission_affects_score is not None:
            hw.late_submission_affects_score = payload.late_submission_affects_score
        updated += 1

    db.commit()
    return {
        "updated": updated,
        "missing_ids": missing,
        "forbidden_ids": forbidden,
    }


@router.get("/{homework_id}", response_model=HomeworkResponse)
def get_homework(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    submission = None
    if current_user.role == UserRole.STUDENT:
        student = _match_student_for_user(db.query(Student).filter(Student.class_id == homework.class_id), current_user)
        if student:
            submission = _get_submission_summary(db, homework.id, student.id)
            if submission:
                refresh_submission_summary(db, submission)
    return _serialize_homework_for_user(homework, current_user, submission)


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
        max_score=data.max_score,
        grade_precision=data.grade_precision,
        auto_grading_enabled=data.auto_grading_enabled,
        rubric_text=data.rubric_text,
        reference_answer=data.reference_answer,
        response_language=data.response_language,
        allow_late_submission=data.allow_late_submission,
        late_submission_affects_score=data.late_submission_affects_score,
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
        previous_homework_attachment = homework.attachment_url
        homework.attachment_name = None
        homework.attachment_url = None
        delete_attachment_file_if_unreferenced(db, previous_homework_attachment)
    elif data.attachment_url is not None:
        previous_attachment_url = homework.attachment_url
        homework.attachment_name = data.attachment_name
        homework.attachment_url = data.attachment_url
        if previous_attachment_url and previous_attachment_url != data.attachment_url:
            delete_attachment_file_if_unreferenced(db, previous_attachment_url)
    if data.subject_id is not None:
        homework.subject_id = data.subject_id
    if data.due_date is not None:
        homework.due_date = data.due_date
    if data.max_score is not None:
        homework.max_score = data.max_score
    if data.grade_precision is not None:
        homework.grade_precision = data.grade_precision
    if data.auto_grading_enabled is not None:
        homework.auto_grading_enabled = data.auto_grading_enabled
    if data.rubric_text is not None:
        homework.rubric_text = data.rubric_text
    if data.reference_answer is not None:
        homework.reference_answer = data.reference_answer
    if data.response_language is not None:
        homework.response_language = data.response_language
    if data.allow_late_submission is not None:
        homework.allow_late_submission = data.allow_late_submission
    if data.late_submission_affects_score is not None:
        homework.late_submission_affects_score = data.late_submission_affects_score

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
    attachment_urls: set[str] = set()

    attempts = db.query(HomeworkAttempt).filter(HomeworkAttempt.homework_id == homework.id).all()
    for attempt in attempts:
        if attempt.attachment_url:
            attachment_urls.add(attempt.attachment_url)
        db.query(HomeworkScoreCandidate).filter(HomeworkScoreCandidate.attempt_id == attempt.id).delete()
        task_ids = [
            item[0]
            for item in db.query(HomeworkGradingTask.id)
            .filter(HomeworkGradingTask.attempt_id == attempt.id)
            .all()
        ]
        if task_ids:
            db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id.in_(task_ids)).delete(
                synchronize_session=False
            )
        db.query(HomeworkGradingTask).filter(HomeworkGradingTask.attempt_id == attempt.id).delete()
        db.delete(attempt)

    for submission in list(homework.submissions):
        if submission.attachment_url:
            attachment_urls.add(submission.attachment_url)
        db.delete(submission)

    if homework.attachment_url:
        _delete_attachment_if_unreferenced(
            db,
            homework.attachment_url,
            exclude_homework_id=homework.id,
        )
    for attachment_url in attachment_urls:
        _delete_attachment_if_unreferenced(db, attachment_url)

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
    submission = _get_submission_summary(db, homework.id, student.id)
    if not submission:
        return None
    return _serialize_submission(db, submission)


@router.get("/{homework_id}/submission/me/history", response_model=HomeworkSubmissionHistoryResponse)
def get_my_homework_submission_history(
    homework_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    student = _resolve_student_for_user(homework, current_user, db)
    submission = _get_submission_summary(db, homework.id, student.id)
    return _serialize_history(db, submission)


@router.post("/{homework_id}/submission", response_model=HomeworkSubmissionResponse)
def submit_homework(
    homework_id: int,
    data: HomeworkSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    student = _resolve_student_for_user(homework, current_user, db)
    submission = _get_submission_summary(db, homework.id, student.id)

    _ensure_homework_submission_open(homework, data, submission)

    if submission is None:
        submission = HomeworkSubmission(
            homework_id=homework.id,
            student_id=student.id,
            subject_id=homework.subject_id,
            class_id=homework.class_id,
        )
        db.add(submission)
        db.flush()

    next_content = data.content
    next_attachment_name = submission.attachment_name or None
    next_attachment_url = submission.attachment_url or None

    if data.remove_attachment and submission.attachment_url:
        next_attachment_name = None
        next_attachment_url = None

    if data.attachment_url is not None:
        next_attachment_name = data.attachment_name
        next_attachment_url = data.attachment_url

    if not (next_content or next_attachment_url):
        raise HTTPException(status_code=400, detail="Please provide submission content or an attachment.")

    submitted_at = datetime.now(timezone.utc)
    is_late = _is_late_attempt(homework, submitted_at)
    counts_toward = _counts_toward_final_score(homework, is_late)

    submission.content = next_content
    submission.attachment_name = next_attachment_name
    submission.attachment_url = next_attachment_url
    submission.submitted_at = submitted_at

    attempt = HomeworkAttempt(
        homework_id=homework.id,
        student_id=student.id,
        subject_id=homework.subject_id,
        class_id=homework.class_id,
        submission_summary_id=submission.id,
        content=next_content,
        attachment_name=next_attachment_name,
        attachment_url=next_attachment_url,
        is_late=is_late,
        counts_toward_final_score=counts_toward,
        submitted_at=submitted_at,
    )
    db.add(attempt)
    db.flush()

    submission.latest_attempt_id = attempt.id
    submission.latest_task_status = None
    submission.latest_task_error = None

    if homework.auto_grading_enabled:
        queue_grading_task(db, attempt, "new_submission")

    refresh_submission_summary(db, submission)
    db.commit()
    db.refresh(submission)
    return _serialize_submission(db, submission)


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
    for submission in submissions:
        refresh_submission_summary(db, submission)
    submission_map = {submission.student_id: submission for submission in submissions}

    rows: list[HomeworkSubmissionStatusResponse] = []
    if homework.subject_id:
        enrollments = get_enrolled_students(homework.subject_id, db)
        for enrollment in enrollments:
            rows.append(_serialize_submission_status(db, enrollment, submission_map.get(enrollment.student_id)))
    else:
        students = db.query(Student).filter(Student.class_id == homework.class_id).order_by(Student.id.asc()).all()
        for student in students:
            rows.append(_serialize_submission_status(db, None, submission_map.get(student.id), student))

    return HomeworkSubmissionStatusListResponse(total=len(rows), data=rows)


@router.post("/{homework_id}/submissions/batch-regrade", response_model=HomeworkBatchRegradeResponse)
def batch_regrade_homework_submissions(
    homework_id: int,
    payload: HomeworkBatchRegradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can regrade homework submissions.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    if not homework.auto_grading_enabled:
        raise HTTPException(status_code=400, detail="This homework does not have auto grading enabled.")

    if not payload.only_latest_attempt:
        raise HTTPException(status_code=400, detail="only_latest_attempt=false is not supported yet.")

    q = db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id == homework.id)
    if payload.submission_ids:
        q = q.filter(HomeworkSubmission.id.in_(payload.submission_ids))
    submissions = q.order_by(HomeworkSubmission.id.asc()).all()

    results: list[HomeworkBatchRegradeItemResult] = []
    queued = 0
    skipped = 0
    for sub in submissions:
        if not sub.latest_attempt_id:
            results.append(
                HomeworkBatchRegradeItemResult(submission_id=sub.id, status="skipped", reason="no_attempt")
            )
            skipped += 1
            continue
        attempt = (
            db.query(HomeworkAttempt)
            .filter(
                HomeworkAttempt.id == sub.latest_attempt_id,
                HomeworkAttempt.submission_summary_id == sub.id,
            )
            .first()
        )
        if not attempt:
            results.append(
                HomeworkBatchRegradeItemResult(submission_id=sub.id, status="skipped", reason="attempt_not_found")
            )
            skipped += 1
            continue
        queue_grading_task(db, attempt, "regrade")
        refresh_submission_summary(db, sub)
        results.append(HomeworkBatchRegradeItemResult(submission_id=sub.id, status="queued", reason=None))
        queued += 1

    db.commit()
    return HomeworkBatchRegradeResponse(queued=queued, skipped=skipped, results=results)


@router.get("/{homework_id}/submissions/{submission_id}/history", response_model=HomeworkSubmissionHistoryResponse)
def get_homework_submission_history(
    homework_id: int,
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can view homework histories.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    submission = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.id == submission_id,
            HomeworkSubmission.homework_id == homework.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Homework submission not found.")
    return _serialize_history(db, submission)


@router.put("/{homework_id}/submissions/{submission_id}/review", response_model=HomeworkSubmissionResponse)
def review_homework_submission(
    homework_id: int,
    submission_id: int,
    payload: HomeworkSubmissionReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can review homework submissions.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    submission = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.id == submission_id,
            HomeworkSubmission.homework_id == homework.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Homework submission not found.")

    if payload.review_score > homework.max_score:
        raise HTTPException(status_code=400, detail=f"Review score must be between 0 and {homework.max_score}.")

    attempt = _resolve_target_attempt(db, submission, payload.attempt_id)
    candidate = HomeworkScoreCandidate(
        attempt_id=attempt.id,
        homework_id=homework.id,
        student_id=submission.student_id,
        source="teacher",
        score=normalize_score_for_homework(homework, payload.review_score),
        comment=payload.review_comment,
        created_by=current_user.id,
        source_metadata={"submission_id": submission.id},
    )
    db.add(candidate)
    refresh_submission_summary(db, submission)
    db.commit()
    db.refresh(submission)
    return _serialize_submission(db, submission)


@router.post("/{homework_id}/submissions/{submission_id}/regrade", response_model=HomeworkSubmissionResponse)
def regrade_homework_submission(
    homework_id: int,
    submission_id: int,
    payload: HomeworkRegradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not is_teacher(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can regrade homework submissions.")

    homework = _ensure_homework_access(_get_homework_or_404(homework_id, db), current_user, db)
    if not homework.auto_grading_enabled:
        raise HTTPException(status_code=400, detail="This homework does not have auto grading enabled.")

    submission = (
        db.query(HomeworkSubmission)
        .filter(
            HomeworkSubmission.id == submission_id,
            HomeworkSubmission.homework_id == homework.id,
        )
        .first()
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Homework submission not found.")

    attempt = _resolve_target_attempt(db, submission, payload.attempt_id)
    queue_grading_task(db, attempt, "regrade")
    refresh_submission_summary(db, submission)
    db.commit()
    db.refresh(submission)
    return _serialize_submission(db, submission)


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
            attempt = submission.latest_attempt
            attachment_url = attempt.attachment_url if attempt and attempt.attachment_url else submission.attachment_url
            attachment_name = attempt.attachment_name if attempt and attempt.attachment_name else submission.attachment_name
            file_path = get_attachment_file_path(attachment_url)
            if not file_path or not file_path.exists():
                continue

            original_name = Path(attachment_name or file_path.name).name
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
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return StreamingResponse(archive_buffer, media_type="application/zip", headers=headers)
