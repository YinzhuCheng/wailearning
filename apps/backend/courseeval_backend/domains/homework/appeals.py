"""Teacher notifications for student homework grade appeals."""

from __future__ import annotations

from sqlalchemy.orm import Session

from apps.backend.courseeval_backend.domains.courses.access import subject_teacher_user_ids
from apps.backend.courseeval_backend.db.models import Homework, HomeworkGradeAppeal, Notification


def notify_teachers_grade_appeal(
    db: Session,
    *,
    appeal: HomeworkGradeAppeal,
    homework: Homework,
    student_name: str,
    creator_user_id: int,
) -> list[Notification]:
    """Create one teacher-targeted notification per course teacher + class teacher."""
    if not homework.subject_id:
        return []

    teacher_ids = subject_teacher_user_ids(db, int(homework.subject_id))
    created: list[Notification] = []
    title = f"成绩申诉待处理：{homework.title}"
    excerpt = (appeal.reason_text or "").strip()
    if len(excerpt) > 500:
        excerpt = excerpt[:500] + "…"
    body_lines = [
        f"学生 {student_name} 对作业《{homework.title}》提交了成绩申诉。",
        f"申诉编号：{appeal.id}",
        "申诉理由：",
        excerpt or "（无）",
        "",
        "请在“作业 -> 学生提交”中打开对应学生，查看详情并调整分数。",
    ]
    content = "\n".join(body_lines)

    for uid in teacher_ids:
        existing = (
            db.query(Notification)
            .filter(
                Notification.related_appeal_id == appeal.id,
                Notification.target_user_id == uid,
                Notification.notification_kind == "grade_appeal",
            )
            .first()
        )
        if existing:
            existing.title = title
            existing.content = content
            existing.class_id = homework.class_id
            existing.subject_id = homework.subject_id
            existing.related_homework_id = homework.id
            existing.related_student_id = appeal.student_id
            existing.created_by = creator_user_id
            created.append(existing)
            continue

        row = Notification(
            title=title,
            content=content,
            priority="important",
            is_pinned=False,
            class_id=homework.class_id,
            subject_id=homework.subject_id,
            target_student_id=None,
            target_user_id=uid,
            related_homework_id=homework.id,
            related_student_id=appeal.student_id,
            related_appeal_id=appeal.id,
            notification_kind="grade_appeal",
            created_by=creator_user_id,
        )
        db.add(row)
        created.append(row)

    return created


def mark_appeal_notifications_acknowledged(db: Session, appeal_id: int) -> None:
    """Mark teacher notifications as acknowledged without implying the appeal is resolved."""
    rows = db.query(Notification).filter(Notification.related_appeal_id == appeal_id).all()
    for row in rows:
        if row.notification_kind != "grade_appeal":
            continue
        title = str(row.title or "")
        if title.startswith("【已阅】") or title.startswith("【已处理】"):
            continue
        row.title = "【已阅】" + title
        row.content = (row.content or "") + "\n\n【系统】教师已确认收到申诉。"


def mark_appeal_notifications_resolved(db: Session, appeal_id: int) -> None:
    """Mark teacher notifications as handled after the appeal is actually resolved."""
    rows = db.query(Notification).filter(Notification.related_appeal_id == appeal_id).all()
    for row in rows:
        if row.notification_kind != "grade_appeal":
            continue
        title = str(row.title or "")
        if title.startswith("【已处理】"):
            continue
        if title.startswith("【已阅】"):
            title = title[len("【已阅】") :]
        row.title = "【已处理】" + title
        row.content = (row.content or "") + "\n\n【系统】教师已处理该申诉。"
