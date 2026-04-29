from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.course_access import ensure_course_access
from app.database import get_db
from app.models import Attendance, Class, Homework, HomeworkAttempt, HomeworkSubmission, Score, Student, Subject, User
from app.schemas import (
    ClassRanking,
    DashboardStats,
    HomeworkLearningAnalyticsResponse,
    HomeworkResubmitLift,
    HomeworkTrendPoint,
    ScoreResponse,
    StudentRanking,
)
from app.routers.classes import apply_class_id_filter, get_accessible_class_ids


router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


def _apply_course_scope(subject_id: Optional[int], current_user: User, db: Session):
    selected_course = None
    if subject_id:
        try:
            selected_course = ensure_course_access(subject_id, current_user, db)
        except ValueError:
            raise HTTPException(status_code=404, detail="Course not found.")
        except PermissionError:
            raise HTTPException(status_code=403, detail="You do not have access to this course.")
    return selected_course


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    semester: Optional[str] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    selected_course = _apply_course_scope(subject_id, current_user, db)
    class_ids = get_accessible_class_ids(current_user, db)
    if selected_course and selected_course.class_id:
        class_ids = [selected_course.class_id]

    total_students_query = apply_class_id_filter(db.query(Student), Student.class_id, class_ids)
    total_students = total_students_query.count()
    total_classes = len(class_ids)

    score_query = apply_class_id_filter(db.query(Score), Score.class_id, class_ids)
    if semester:
        score_query = score_query.filter(Score.semester == semester)
    if selected_course:
        score_query = score_query.filter(Score.subject_id == selected_course.id)

    total_scores = score_query.count()
    avg_score = round(score_query.with_entities(func.avg(Score.score)).scalar() or 0, 2)

    attendance_query = apply_class_id_filter(db.query(Attendance), Attendance.class_id, class_ids)
    if selected_course:
        attendance_query = attendance_query.filter(Attendance.subject_id == selected_course.id)

    latest_attendance_date = attendance_query.with_entities(func.max(Attendance.date)).scalar()
    if latest_attendance_date:
        latest_attendance_query = attendance_query.filter(Attendance.date == latest_attendance_date)
        total_attendance = latest_attendance_query.count()
        present_attendance = latest_attendance_query.filter(Attendance.status == "present").count()
        attendance_rate = round((present_attendance / total_attendance) * 100, 2) if total_attendance else 0
    else:
        attendance_rate = 0

    recent_scores = score_query.order_by(Score.created_at.desc()).limit(10).all()
    recent_score_list = []
    for score in recent_scores:
        recent_score_list.append(
            ScoreResponse(
                id=score.id,
                student_id=score.student_id,
                subject_id=score.subject_id,
                class_id=score.class_id,
                score=score.score,
                exam_type=score.exam_type,
                exam_date=score.exam_date,
                semester=score.semester,
                created_at=score.created_at,
                student_name=score.student.name if score.student else None,
                subject_name=score.subject.name if score.subject else None,
                class_name=score.class_obj.name if score.class_obj else None,
            )
        )

    return DashboardStats(
        total_students=total_students,
        total_classes=total_classes,
        total_scores=total_scores,
        avg_score=avg_score,
        attendance_rate=attendance_rate,
        recent_scores=recent_score_list,
        class_rankings=[],
    )


@router.get("/rankings/classes", response_model=list[ClassRanking])
def get_class_rankings(
    semester: Optional[str] = None,
    exam_type: Optional[str] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    selected_course = _apply_course_scope(subject_id, current_user, db)
    class_ids = get_accessible_class_ids(current_user, db)
    if selected_course and selected_course.class_id:
        class_ids = [selected_course.class_id]

    query = db.query(
        Score.class_id,
        func.avg(Score.score).label("avg_score"),
    )
    query = apply_class_id_filter(query, Score.class_id, class_ids)

    if semester:
        query = query.filter(Score.semester == semester)
    if exam_type:
        query = query.filter(Score.exam_type == exam_type)
    if selected_course:
        query = query.filter(Score.subject_id == selected_course.id)

    results = query.group_by(Score.class_id).order_by(func.avg(Score.score).desc()).all()

    rankings = []
    for rank, (class_id, avg_score) in enumerate(results, 1):
        class_obj = db.query(Class).filter(Class.id == class_id).first()
        rankings.append(
            ClassRanking(
                class_id=class_id,
                class_name=class_obj.name if class_obj else "",
                avg_score=round(avg_score, 2) if avg_score else 0,
                rank=rank,
            )
        )

    return rankings


@router.get("/rankings/students", response_model=list[StudentRanking])
def get_student_rankings(
    class_id: Optional[int] = None,
    semester: Optional[str] = None,
    exam_type: Optional[str] = None,
    subject_id: Optional[int] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    selected_course = _apply_course_scope(subject_id, current_user, db)
    class_ids = get_accessible_class_ids(current_user, db)
    if selected_course and selected_course.class_id:
        class_ids = [selected_course.class_id]

    query = db.query(
        Score.student_id,
        func.avg(Score.score).label("avg_score"),
    )
    query = apply_class_id_filter(query, Score.class_id, class_ids)

    if class_id:
        if class_id not in class_ids:
            raise HTTPException(status_code=403, detail="You do not have access to this class.")
        query = query.filter(Score.class_id == class_id)
    if semester:
        query = query.filter(Score.semester == semester)
    if exam_type:
        query = query.filter(Score.exam_type == exam_type)
    if selected_course:
        query = query.filter(Score.subject_id == selected_course.id)

    results = query.group_by(Score.student_id).order_by(func.avg(Score.score).desc()).limit(limit).all()

    rankings = []
    for rank, (student_id, avg_score) in enumerate(results, 1):
        student = db.query(Student).filter(Student.id == student_id).first()
        class_obj = db.query(Class).filter(Class.id == student.class_id).first() if student else None
        rankings.append(
            StudentRanking(
                student_id=student_id,
                student_name=student.name if student else "",
                class_name=class_obj.name if class_obj else "",
                avg_score=round(avg_score, 2) if avg_score else 0,
                rank=rank,
            )
        )
    return rankings


@router.get("/rankings/subjects/{subject_id}")
def get_subject_rankings(
    subject_id: int,
    class_id: Optional[int] = None,
    semester: Optional[str] = None,
    exam_type: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    selected_course = _apply_course_scope(subject_id, current_user, db)
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id:
        if class_id not in class_ids:
            raise HTTPException(status_code=403, detail="You do not have access to this class.")
        class_ids = [class_id]

    query = apply_class_id_filter(db.query(Score), Score.class_id, class_ids)
    if semester:
        query = query.filter(Score.semester == semester)
    if exam_type:
        query = query.filter(Score.exam_type == exam_type)

    scores = query.order_by(Score.score.desc()).limit(limit).all()
    results = []
    for rank, score in enumerate(scores, 1):
        results.append(
            {
                "rank": rank,
                "student_id": score.student_id,
                "student_name": score.student.name if score.student else "",
                "score": score.score,
                "subject_name": score.subject.name if score.subject else "",
                "exam_type": score.exam_type,
                "semester": score.semester,
            }
        )
    return results


@router.get("/analysis/trends")
def get_score_trends(
    semester: Optional[str] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    selected_course = _apply_course_scope(subject_id, current_user, db)
    class_ids = get_accessible_class_ids(current_user, db)
    query = apply_class_id_filter(db.query(Score), Score.class_id, class_ids)
    if semester:
        query = query.filter(Score.semester == semester)
    if selected_course:
        query = query.filter(Score.subject_id == selected_course.id)

    scores = query.all()
    exam_types = {}
    for score in scores:
        exam_types.setdefault(score.exam_type, []).append(score.score)

    trends = {}
    for exam_type, score_list in exam_types.items():
        trends[exam_type] = {
            "avg": round(sum(score_list) / len(score_list), 2),
            "max": max(score_list),
            "min": min(score_list),
            "count": len(score_list),
        }
    return trends


@router.get("/analysis/subjects")
def get_subject_analysis(
    semester: Optional[str] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    selected_course = _apply_course_scope(subject_id, current_user, db)
    class_ids = get_accessible_class_ids(current_user, db)
    query = db.query(
        Score.subject_id,
        func.avg(Score.score).label("avg_score"),
        func.max(Score.score).label("max_score"),
        func.min(Score.score).label("min_score"),
        func.count(Score.id).label("count"),
    )
    query = apply_class_id_filter(query, Score.class_id, class_ids)

    if semester:
        query = query.filter(Score.semester == semester)
    if selected_course:
        query = query.filter(Score.subject_id == selected_course.id)

    results = query.group_by(Score.subject_id).all()
    analysis = []
    for current_subject_id, avg_score, max_score, min_score, count in results:
        subject = db.query(Subject).filter(Subject.id == current_subject_id).first()
        analysis.append(
            {
                "subject_id": current_subject_id,
                "subject_name": subject.name if subject else "",
                "avg_score": round(avg_score, 2) if avg_score else 0,
                "max_score": max_score,
                "min_score": min_score,
                "count": count,
            }
        )
    return analysis


@router.get("/analysis/homework-learning", response_model=HomeworkLearningAnalyticsResponse)
def get_homework_learning_analytics(
    semester: Optional[str] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Per-course homework analytics: class trend and resubmission score lift."""
    from app.routers.homework import _best_candidate_for_attempt

    selected_course = _apply_course_scope(subject_id, current_user, db)
    if not selected_course:
        raise HTTPException(status_code=400, detail="subject_id is required for homework learning analytics.")

    class_ids = get_accessible_class_ids(current_user, db)
    if selected_course.class_id:
        class_ids = [selected_course.class_id]

    hw_base = db.query(Homework).filter(Homework.subject_id == selected_course.id)
    if class_ids:
        hw_base = hw_base.filter(Homework.class_id.in_(class_ids))
    if semester:
        hw_base = hw_base.join(Subject, Subject.id == Homework.subject_id).filter(Subject.semester == semester)

    homework_rows = hw_base.order_by(Homework.due_date.asc().nullslast(), Homework.id.asc()).all()
    if not homework_rows:
        return HomeworkLearningAnalyticsResponse(homework_trend=[], resubmit_lift=[])

    hw_ids = [h.id for h in homework_rows]

    sub_stats = (
        db.query(
            HomeworkSubmission.homework_id,
            func.avg(HomeworkSubmission.review_score).label("avg_s"),
            func.count(HomeworkSubmission.id).label("n_sub"),
            func.sum(case((HomeworkSubmission.review_score.isnot(None), 1), else_=0)).label("n_scored"),
        )
        .filter(HomeworkSubmission.homework_id.in_(hw_ids))
        .group_by(HomeworkSubmission.homework_id)
        .all()
    )
    stats_by_hw = {row.homework_id: row for row in sub_stats}

    homework_trend: list[HomeworkTrendPoint] = []
    for hw in homework_rows:
        row = stats_by_hw.get(hw.id)
        avg_score = round(float(row.avg_s), 2) if row and row.avg_s is not None else 0.0
        submission_count = int(row.n_sub) if row else 0
        scored_count = int(row.n_scored) if row else 0
        homework_trend.append(
            HomeworkTrendPoint(
                homework_id=hw.id,
                title=hw.title,
                due_date=hw.due_date,
                avg_score=avg_score,
                scored_count=scored_count,
                submission_count=submission_count,
            )
        )

    attempt_rows = (
        db.query(HomeworkAttempt)
        .filter(
            HomeworkAttempt.homework_id.in_(hw_ids),
            HomeworkAttempt.submission_summary_id.isnot(None),
        )
        .order_by(
            HomeworkAttempt.homework_id,
            HomeworkAttempt.student_id,
            HomeworkAttempt.submitted_at.asc(),
            HomeworkAttempt.id.asc(),
        )
        .all()
    )

    by_hw_student: dict[int, dict[int, list[HomeworkAttempt]]] = defaultdict(lambda: defaultdict(list))
    for att in attempt_rows:
        by_hw_student[att.homework_id][att.student_id].append(att)

    resubmit_lift: list[HomeworkResubmitLift] = []
    hw_by_id = {h.id: h for h in homework_rows}

    for hw_id, student_map in by_hw_student.items():
        first_scores: list[float] = []
        last_scores: list[float] = []
        for _stu_id, attempts in student_map.items():
            if len(attempts) < 2:
                continue
            first_c = _best_candidate_for_attempt(db, attempts[0].id)
            last_c = _best_candidate_for_attempt(db, attempts[-1].id)
            if first_c is None or last_c is None:
                continue
            first_scores.append(float(first_c.score))
            last_scores.append(float(last_c.score))

        if not first_scores:
            continue

        hw = hw_by_id.get(hw_id)
        title = hw.title if hw else ""
        n = len(first_scores)
        avg_first = round(sum(first_scores) / n, 2)
        avg_last = round(sum(last_scores) / n, 2)
        resubmit_lift.append(
            HomeworkResubmitLift(
                homework_id=hw_id,
                title=title,
                student_count=n,
                avg_first_score=avg_first,
                avg_last_score=avg_last,
                avg_lift=round(avg_last - avg_first, 2),
            )
        )

    resubmit_lift.sort(key=lambda x: (-x.student_count, x.homework_id))

    return HomeworkLearningAnalyticsResponse(homework_trend=homework_trend, resubmit_lift=resubmit_lift)
