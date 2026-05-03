"""Teacher notifications for course score (composition) appeals."""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.backend.wailearning_backend.course_access import subject_teacher_user_ids
from apps.backend.wailearning_backend.db.models import Notification, ScoreGradeAppeal, Subject


def notify_teachers_score_grade_appeal(
    db: Session,
    *,
    appeal: ScoreGradeAppeal,
    student_name: str,
    creator_user_id: int,
) -> list[Notification]:
    course = db.query(Subject).filter(Subject.id == appeal.subject_id).first()
    class_id = course.class_id if course else None
    teacher_ids = subject_teacher_user_ids(db, int(appeal.subject_id))
    created: list[Notification] = []
    title = "成绩构成申诉待处理"
    excerpt = (appeal.reason_text or "").strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:500] + "…"
    body_lines = [
        f"学生 {student_name} 提交了成绩申诉。",
        f"申诉编号：{appeal.id}",
        f"学期：{appeal.semester}",
        f"申诉对象：{appeal.target_component}",
        "申诉理由：",
        excerpt or "（无）",
        "",
        "请在「成绩管理」中查看学生成绩构成并处理。",
    ]
    content = "\n".join(body_lines)

    for uid in teacher_ids:
        existing = (
            db.query(Notification)
            .filter(
                Notification.related_score_appeal_id == appeal.id,
                Notification.target_user_id == uid,
                Notification.notification_kind == "score_grade_appeal",
            )
            .first()
        )
        if existing:
            existing.title = title
            existing.content = content
            existing.class_id = class_id
            existing.subject_id = appeal.subject_id
            existing.related_student_id = appeal.student_id
            existing.created_by = creator_user_id
            created.append(existing)
            continue
        n = Notification(
            title=title,
            content=content,
            priority="important",
            is_pinned=False,
            class_id=class_id,
            subject_id=appeal.subject_id,
            target_student_id=None,
            target_user_id=uid,
            related_homework_id=None,
            related_student_id=appeal.student_id,
            related_appeal_id=None,
            related_score_appeal_id=appeal.id,
            notification_kind="score_grade_appeal",
            created_by=creator_user_id,
        )
        db.add(n)
        created.append(n)
    return created


def mark_score_appeal_notifications_handled(db: Session, appeal_id: int) -> None:
    rows = db.query(Notification).filter(Notification.related_score_appeal_id == appeal_id).all()
    for n in rows:
        if n.notification_kind == "score_grade_appeal" and not str(n.title or "").startswith("【已处理】"):
            n.title = "【已处理】" + str(n.title or "")
            n.content = (n.content or "") + "\n\n【系统】教师已回复该申诉。"
