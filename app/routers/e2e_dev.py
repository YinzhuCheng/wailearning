"""Ephemeral test data for Playwright / local E2E. Disabled unless E2E_DEV_SEED_ENABLED and token match."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.config import settings
from app.database import get_db
from app.models import Class, CourseEnrollment, Gender, Homework, Student, Subject, User, UserRole

router = APIRouter(prefix="/api/e2e", tags=["e2e-dev"])


def _require_seed_token(x_e2e_seed_token: str | None) -> None:
    if not settings.E2E_DEV_SEED_ENABLED:
        raise HTTPException(status_code=404, detail="E2E dev seed is disabled.")
    expected = (settings.E2E_DEV_SEED_TOKEN or "").strip()
    if not expected or (x_e2e_seed_token or "").strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid E2E seed token.")


@router.post("/dev/reset-scenario")
def reset_e2e_scenario(
    x_e2e_seed_token: str | None = Header(None, alias="X-E2E-Seed-Token"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Create isolated users/classes/courses for UI tests. Safe to call repeatedly (new suffix each time).
    """
    _require_seed_token(x_e2e_seed_token)

    suffix = uuid.uuid4().hex[:10]
    pwd = "E2eTest1!"
    hpwd = get_password_hash(pwd)

    c1 = Class(name=f"E2E甲班_{suffix}", grade=2026)
    c2 = Class(name=f"E2E乙班_{suffix}", grade=2026)
    db.add_all([c1, c2])
    db.flush()

    admin = User(
        username=f"e2e_adm_{suffix}",
        hashed_password=get_password_hash("E2eAdmin1!"),
        real_name="E2E管理员",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    t_own = User(
        username=f"e2e_teach_own_{suffix}",
        hashed_password=hpwd,
        real_name=f"E2E任课甲_{suffix}",
        role=UserRole.TEACHER.value,
        is_active=True,
    )
    t_other = User(
        username=f"e2e_teach_other_{suffix}",
        hashed_password=hpwd,
        real_name=f"E2E任课乙_{suffix}",
        role=UserRole.TEACHER.value,
        is_active=True,
    )
    db.add_all([admin, t_own, t_other])
    db.flush()

    st_plain = Student(
        name="E2E学生甲",
        student_no=f"e2e_stu_plain_{suffix}",
        gender=Gender.MALE,
        class_id=c1.id,
    )
    st_drop = Student(
        name="E2E退选生",
        student_no=f"e2e_stu_drop_{suffix}",
        gender=Gender.MALE,
        class_id=c1.id,
    )
    st_b = Student(
        name="E2E学生乙",
        student_no=f"e2e_stu_b_{suffix}",
        gender=Gender.FEMALE,
        class_id=c1.id,
    )
    db.add_all([st_plain, st_drop, st_b])
    db.flush()

    u_plain = User(
        username=st_plain.student_no,
        hashed_password=hpwd,
        real_name=st_plain.name,
        role=UserRole.STUDENT.value,
        class_id=c1.id,
        is_active=True,
    )
    u_drop = User(
        username=st_drop.student_no,
        hashed_password=hpwd,
        real_name=st_drop.name,
        role=UserRole.STUDENT.value,
        class_id=c1.id,
        is_active=True,
    )
    u_b = User(
        username=st_b.student_no,
        hashed_password=hpwd,
        real_name=st_b.name,
        role=UserRole.STUDENT.value,
        class_id=c1.id,
        is_active=True,
    )
    db.add_all([u_plain, u_drop, u_b])
    db.flush()

    course_req = Subject(
        name=f"E2E必修课_{suffix}",
        teacher_id=t_own.id,
        class_id=c1.id,
        course_type="required",
        status="active",
    )
    course_el = Subject(
        name=f"E2E选修课_{suffix}",
        teacher_id=t_own.id,
        class_id=c1.id,
        course_type="elective",
        status="active",
    )
    course_other = Subject(
        name=f"E2E乙班课_{suffix}",
        teacher_id=t_other.id,
        class_id=c2.id,
        course_type="required",
        status="active",
    )
    course_orphan = Subject(
        name=f"E2E无班级课_{suffix}",
        teacher_id=t_own.id,
        class_id=None,
        course_type="required",
        status="active",
    )
    db.add_all([course_req, course_el, course_other, course_orphan])
    db.flush()

    # st_plain / st_drop 已在必修课；st_b 仅在花名册，用于「从花名册进课」勾选
    for st in (st_plain, st_drop):
        db.add(
            CourseEnrollment(
                subject_id=course_req.id,
                student_id=st.id,
                class_id=c1.id,
                enrollment_type="required",
                can_remove=False,
            )
        )

    hw = Homework(
        title=f"E2E_UI作业_{suffix}",
        content="用于 Playwright UI 测试的作业说明。",
        class_id=c1.id,
        subject_id=course_req.id,
        max_score=100.0,
        grade_precision="integer",
        auto_grading_enabled=True,
        allow_late_submission=True,
        late_submission_affects_score=False,
        created_by=t_own.id,
    )
    db.add(hw)

    db.commit()

    return {
        "suffix": suffix,
        "password_teacher_student": pwd,
        "password_admin": "E2eAdmin1!",
        "admin": {"username": admin.username, "password": "E2eAdmin1!"},
        "teacher_own": {"username": t_own.username, "password": pwd},
        "teacher_other": {"username": t_other.username, "password": pwd},
        "student_plain": {"username": u_plain.username, "password": pwd, "student_row_id": st_plain.id},
        "student_drop": {"username": u_drop.username, "password": pwd, "student_row_id": st_drop.id},
        "student_b": {"username": u_b.username, "password": pwd, "student_row_id": st_b.id},
        "class_id_1": c1.id,
        "class_id_2": c2.id,
        "class_name_1": c1.name,
        "course_required_id": course_req.id,
        "course_elective_id": course_el.id,
        "course_other_teacher_id": course_other.id,
        "course_orphan_id": course_orphan.id,
        "homework_id": hw.id,
        "user_ids_for_batch": [u_plain.id, u_b.id],
        "teacher_user_id": t_own.id,
    }
