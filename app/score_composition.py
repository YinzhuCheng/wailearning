"""Course grade composition: homework avg, other daily (manual), exams (manual), weighted total."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import CourseExamWeight, CourseGradeScheme, Homework, HomeworkSubmission, Score, Student, Subject


OTHER_DAILY_EXAM_TYPE = "其他平时分"


@dataclass
class CourseGradeSchemeDTO:
    homework_weight: float
    extra_daily_weight: float


def get_scheme_dto(db: Session, subject_id: int) -> CourseGradeSchemeDTO:
    row = db.query(CourseGradeScheme).filter(CourseGradeScheme.subject_id == subject_id).first()
    if row:
        return CourseGradeSchemeDTO(
            homework_weight=float(row.homework_weight or 0),
            extra_daily_weight=float(row.extra_daily_weight or 0),
        )
    return CourseGradeSchemeDTO(homework_weight=30.0, extra_daily_weight=20.0)


def upsert_scheme(db: Session, subject_id: int, homework_weight: float, extra_daily_weight: float) -> CourseGradeScheme:
    row = db.query(CourseGradeScheme).filter(CourseGradeScheme.subject_id == subject_id).first()
    if row:
        row.homework_weight = homework_weight
        row.extra_daily_weight = extra_daily_weight
    else:
        row = CourseGradeScheme(
            subject_id=subject_id,
            homework_weight=homework_weight,
            extra_daily_weight=extra_daily_weight,
        )
        db.add(row)
    db.flush()
    return row


def _homework_weighted_percent(sub: HomeworkSubmission, hw: Homework) -> float:
    mx = float(hw.max_score or 100) or 100.0
    if mx <= 0:
        mx = 100.0
    return (float(sub.review_score or 0) / mx) * 100.0


def compute_homework_average_percent(db: Session, *, student_id: int, subject_id: int) -> Optional[float]:
    """Mean of (review_score/max_score*100) over homeworks in this course with a scored submission."""
    q = (
        db.query(func.avg(HomeworkSubmission.review_score / func.nullif(Homework.max_score, 0) * 100.0))
        .join(Homework, Homework.id == HomeworkSubmission.homework_id)
        .filter(
            Homework.subject_id == subject_id,
            HomeworkSubmission.student_id == student_id,
            HomeworkSubmission.review_score.isnot(None),
            Homework.max_score.isnot(None),
            Homework.max_score > 0,
        )
    )
    val = q.scalar()
    if val is None:
        return None
    return round(float(val), 2)


def compute_homework_average_percent_python(db: Session, *, student_id: int, subject_id: int) -> Optional[float]:
    """SQLite-safe: compute in Python."""
    rows = (
        db.query(HomeworkSubmission, Homework)
        .join(Homework, Homework.id == HomeworkSubmission.homework_id)
        .filter(
            Homework.subject_id == subject_id,
            HomeworkSubmission.student_id == student_id,
            HomeworkSubmission.review_score.isnot(None),
        )
        .all()
    )
    if not rows:
        return None
    parts = [_homework_weighted_percent(sub, hw) for sub, hw in rows]
    return round(sum(parts) / len(parts), 2)


def exam_weights_total(db: Session, subject_id: int) -> float:
    total = (
        db.query(func.sum(CourseExamWeight.weight))
        .filter(CourseExamWeight.subject_id == subject_id)
        .scalar()
    )
    return float(total or 0)


def get_exam_weight_rows(db: Session, subject_id: int) -> list:
    return (
        db.query(CourseExamWeight)
        .filter(CourseExamWeight.subject_id == subject_id)
        .order_by(CourseExamWeight.exam_type.asc())
        .all()
    )


def build_composition_for_student(
    db: Session,
    *,
    student_id: int,
    subject_id: int,
    semester: str,
    use_sql_avg: bool = True,
    student_name: Optional[str] = None,
) -> dict:
    """Assemble components and weighted total for one student / course / semester."""
    course = db.query(Subject).filter(Subject.id == subject_id).first()
    st_row = db.query(Student).filter(Student.id == student_id).first()
    scheme = get_scheme_dto(db, subject_id)
    exam_rows = get_exam_weight_rows(db, subject_id)
    exam_total_w = sum(float(r.weight) for r in exam_rows)

    if use_sql_avg:
        try:
            hw_avg = compute_homework_average_percent(db, student_id=student_id, subject_id=subject_id)
        except Exception:
            hw_avg = compute_homework_average_percent_python(db, student_id=student_id, subject_id=subject_id)
    else:
        hw_avg = compute_homework_average_percent_python(db, student_id=student_id, subject_id=subject_id)

    other_row = (
        db.query(Score)
        .filter(
            Score.student_id == student_id,
            Score.subject_id == subject_id,
            Score.semester == semester,
            Score.exam_type == OTHER_DAILY_EXAM_TYPE,
        )
        .first()
    )
    other_score = float(other_row.score) if other_row else None

    exam_scores: dict[str, float] = {}
    for wrow in exam_rows:
        et = wrow.exam_type
        sc = (
            db.query(Score)
            .filter(
                Score.student_id == student_id,
                Score.subject_id == subject_id,
                Score.semester == semester,
                Score.exam_type == et,
            )
            .first()
        )
        if sc:
            exam_scores[et] = float(sc.score)

    inner_total = float(scheme.homework_weight) + float(scheme.extra_daily_weight) + exam_total_w
    inner_ok = round(inner_total, 2) == 100.0

    total: Optional[float] = None
    missing: list[str] = []

    if inner_ok:
        t = 0.0
        if hw_avg is None:
            missing.append("作业平时分（尚无已批改作业）")
        else:
            t += hw_avg * float(scheme.homework_weight) / 100.0

        if other_score is None:
            missing.append(OTHER_DAILY_EXAM_TYPE)
        else:
            t += other_score * float(scheme.extra_daily_weight) / 100.0

        for wrow in exam_rows:
            et = wrow.exam_type
            w = float(wrow.weight)
            if et not in exam_scores:
                missing.append(et)
            else:
                t += exam_scores[et] * w / 100.0

        total = round(t, 2) if not missing else None

    homework_items: list[dict] = []
    for sub, hw in (
        db.query(HomeworkSubmission, Homework)
        .join(Homework, Homework.id == HomeworkSubmission.homework_id)
        .filter(Homework.subject_id == subject_id, HomeworkSubmission.student_id == student_id)
        .order_by(Homework.due_date.asc().nullslast(), Homework.id.asc())
        .all()
    ):
        pct = None
        if sub.review_score is not None:
            pct = round(_homework_weighted_percent(sub, hw), 2)
        homework_items.append(
            {
                "homework_id": hw.id,
                "title": hw.title,
                "max_score": float(hw.max_score or 100),
                "review_score": float(sub.review_score) if sub.review_score is not None else None,
                "percent_equivalent": pct,
            }
        )

    return {
        "student_id": student_id,
        "student_name": student_name if student_name is not None else (st_row.name if st_row else None),
        "student_no": st_row.student_no if st_row else None,
        "subject_id": subject_id,
        "subject_name": course.name if course else "",
        "semester": semester,
        "scheme": {
            "homework_weight": scheme.homework_weight,
            "extra_daily_weight": scheme.extra_daily_weight,
            "other_daily_label": OTHER_DAILY_EXAM_TYPE,
            "exam_weights": [{"exam_type": r.exam_type, "weight": float(r.weight)} for r in exam_rows],
            "inner_parts_sum": round(inner_total, 2),
            "inner_parts_valid": inner_ok,
        },
        "homework_average_percent": hw_avg,
        "homework_assignments": homework_items,
        "other_daily_score": other_score,
        "other_daily_score_id": other_row.id if other_row else None,
        "exam_scores": exam_scores,
        "weighted_total": total,
        "missing_for_total": missing,
    }
