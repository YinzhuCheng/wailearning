"""Student course visibility: class roster union + enrollments after prepare."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models import Class, CourseEnrollment, Gender, Student, Subject, User, UserRole
from app.course_access import prepare_student_course_context


def _seed_student_two_courses(db: Session):
    klass_a = Class(name="班级甲", grade=1)
    klass_b = Class(name="班级乙", grade=1)
    db.add_all([klass_a, klass_b])
    db.flush()

    course_in_a = Subject(
        name="数学甲",
        class_id=klass_a.id,
        course_type="required",
        status="active",
    )
    course_in_b = Subject(
        name="数学乙",
        class_id=klass_b.id,
        course_type="required",
        status="active",
    )
    db.add_all([course_in_a, course_in_b])
    db.flush()

    st = Student(name="张三", student_no="u1", gender=Gender.MALE, class_id=klass_a.id)
    db.add(st)
    db.flush()

    db.add(
        CourseEnrollment(
            subject_id=course_in_a.id,
            student_id=st.id,
            class_id=klass_a.id,
            enrollment_type="required",
            can_remove=False,
        )
    )

    user = User(
        username="u1",
        hashed_password="x",
        real_name="张三",
        role=UserRole.STUDENT.value,
        class_id=klass_a.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(course_in_a)
    db.refresh(course_in_b)
    return user, course_in_a, course_in_b


def test_student_course_list_only_enrolled_subjects():
    db = SessionLocal()
    try:
        user, course_a, course_b = _seed_student_two_courses(db)
    finally:
        db.close()

    client = TestClient(app)
    from app.auth import create_access_token

    token = create_access_token(data={"sub": user.username})
    res = client.get("/api/subjects", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    ids = {item["id"] for item in res.json()}
    assert course_a.id in ids
    assert course_b.id not in ids


def test_prepare_moves_unique_roster_to_user_class_and_enrolls():
    suffix = uuid.uuid4().hex[:8]
    db = SessionLocal()
    try:
        klass_a = Class(name=f"A班_{suffix}", grade=1)
        klass_b = Class(name=f"B班_{suffix}", grade=1)
        db.add_all([klass_a, klass_b])
        db.flush()

        course_a = Subject(name=f"语文A_{suffix}", class_id=klass_a.id, course_type="required", status="active")
        db.add(course_a)
        db.flush()

        stu_no = f"stu_move_{suffix}"
        st = Student(name="李四", student_no=stu_no, gender=Gender.MALE, class_id=klass_b.id)
        db.add(st)
        db.flush()

        user = User(
            username=stu_no,
            hashed_password="x",
            real_name="李四",
            role=UserRole.STUDENT.value,
            class_id=klass_a.id,
        )
        db.add(user)
        db.commit()

        prepare_student_course_context(user, db)
        db.commit()

        db.refresh(st)
        assert st.class_id == klass_a.id
        enr = (
            db.query(CourseEnrollment)
            .filter(CourseEnrollment.student_id == st.id, CourseEnrollment.subject_id == course_a.id)
            .first()
        )
        assert enr is not None
    finally:
        db.close()
