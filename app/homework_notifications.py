"""In-app notifications when a student's homework is graded (teacher or auto)."""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import Homework, HomeworkSubmission, Notification, Student, User, UserRole


def _format_score_display(homework: Homework, score: Optional[float]) -> str:
    if score is None:
        return "—"
    cap = float(homework.max_score or 100)
    value = max(0.0, min(float(score), cap))
    if (homework.grade_precision or "integer") == "decimal_1":
        return f"{round(value, 1)}"
    return f"{int(round(value))}"


def _format_max_score(homework: Homework) -> str:
    cap = float(homework.max_score or 100)
    if (homework.grade_precision or "integer") == "decimal_1":
        return f"{round(cap, 1)}"
    return f"{int(round(cap))}"


def notify_student_homework_graded(
    db: Session,
    *,
    homework: Homework,
    submission: HomeworkSubmission,
    actor_user_id: int,
    source_label: str,
    failure_message: Optional[str] = None,
) -> None:
    """
    Create a class-scoped notification visible to students (and teachers) in that class.
    Idempotent per (homework, student, task outcome) using title prefix + stable suffix in content.
    """
    student = db.query(Student).filter(Student.id == submission.student_id).first()
    if not student or not student.student_no:
        return

    user = (
        db.query(User)
        .filter(User.username == student.student_no, User.role == UserRole.STUDENT.value)
        .first()
    )
    if not user:
        return

    title = f"作业已批改：{homework.title}"
    if failure_message:
        body_lines = [
            f"课程：{homework.subject.name}" if homework.subject else "",
            f"结果：自动评分未能完成（{failure_message.strip()}）。请查看作业详情或联系任课教师。",
        ]
    else:
        score_txt = _format_score_display(homework, submission.review_score)
        max_txt = _format_max_score(homework)
        comment = (submission.review_comment or "").strip()
        body_lines = [
            f"课程：{homework.subject.name}" if homework.subject else "",
            f"当前展示分：{score_txt} / {max_txt}（满分）",
            f"来源：{source_label}",
        ]
        if comment:
            body_lines.append(f"评语：{comment}")

    content = "\n".join(line for line in body_lines if line)

    prev_same = (
        db.query(Notification)
        .filter(
            Notification.created_by == actor_user_id,
            Notification.title == title,
            Notification.class_id == homework.class_id,
            Notification.subject_id == homework.subject_id,
        )
        .order_by(Notification.id.desc())
        .first()
    )
    if prev_same and (prev_same.content or "") == content:
        return

    note = Notification(
        title=title,
        content=content or None,
        priority="normal",
        is_pinned=False,
        class_id=homework.class_id,
        subject_id=homework.subject_id,
        created_by=actor_user_id,
    )
    db.add(note)
