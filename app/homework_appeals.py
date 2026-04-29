"""Teacher notifications for student grade appeals."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Homework, HomeworkGradeAppeal, Notification, Subject, User, UserRole


def subject_teacher_user_ids(db: Session, subject_id: int) -> list[int]:
    course = db.query(Subject).filter(Subject.id == subject_id).first()
    if not course:
        return []
    ids: list[int] = []
    if course.teacher_id:
        ids.append(int(course.teacher_id))
    if course.class_id:
        class_teachers = (
            db.query(User.id)
            .filter(User.role == UserRole.CLASS_TEACHER.value, User.class_id == course.class_id)
            .all()
        )
        ids.extend(int(r[0]) for r in class_teachers)
    return sorted(set(ids))


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
        f"学生 {student_name} 对作业「{homework.title}」提交了成绩申诉。",
        f"申诉编号：{appeal.id}",
        "申诉理由：",
        excerpt or "（无）",
        "",
        "请在「作业 → 学生提交」中打开对应学生，查看详情并调整分数。",
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
        n = Notification(
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
        db.add(n)
        created.append(n)
    return created


def mark_appeal_notifications_acknowledged(db: Session, appeal_id: int) -> None:
    """Soft-update titles after teacher acknowledges."""
    rows = db.query(Notification).filter(Notification.related_appeal_id == appeal_id).all()
    for n in rows:
        if n.notification_kind == "grade_appeal" and not str(n.title or "").startswith("【已处理】"):
            n.title = "【已处理】" + str(n.title or "")
            n.content = (n.content or "") + "\n\n【系统】教师已确认收到申诉。"
