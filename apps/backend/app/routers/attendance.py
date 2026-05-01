from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.course_access import ensure_course_access
from app.database import get_db
from app.models import Attendance, Student, Subject, User, UserRole
from app.routers.classes import apply_class_id_filter, get_accessible_class_ids
from app.schemas import AttendanceCreate, AttendanceListResponse, AttendanceResponse, AttendanceUpdate


router = APIRouter(prefix="/api/attendance", tags=["考勤管理"])


def _ensure_attendance_write_access(current_user: User):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Students cannot modify attendance.")


def _serialize_attendance(attendance: Attendance) -> AttendanceResponse:
    return AttendanceResponse(
        id=attendance.id,
        student_id=attendance.student_id,
        class_id=attendance.class_id,
        subject_id=attendance.subject_id,
        date=attendance.date,
        status=attendance.status,
        remark=attendance.remark,
        created_at=attendance.created_at,
        student_name=attendance.student.name if attendance.student else None,
        class_name=attendance.class_obj.name if attendance.class_obj else None,
        subject_name=attendance.subject.name if attendance.subject else None,
    )


@router.get("", response_model=AttendanceListResponse)
def get_attendances(
    class_id: Optional[int] = None,
    student_id: Optional[int] = None,
    student_name: Optional[str] = None,
    subject_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    class_ids = get_accessible_class_ids(current_user, db)
    query = apply_class_id_filter(db.query(Attendance), Attendance.class_id, class_ids)

    if class_id:
        if class_id not in class_ids:
            raise HTTPException(status_code=403, detail="You do not have access to this class.")
        query = query.filter(Attendance.class_id == class_id)
    if student_id:
        query = query.filter(Attendance.student_id == student_id)
    if student_name:
        query = query.join(Student, Attendance.student_id == Student.id).filter(Student.name.contains(student_name))
    if subject_id:
        ensure_course_access(subject_id, current_user, db)
        query = query.filter(Attendance.subject_id == subject_id)
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)
    if status:
        query = query.filter(Attendance.status == status)

    total = query.count()
    attendances = query.order_by(Attendance.date.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return AttendanceListResponse(total=total, data=[_serialize_attendance(attendance) for attendance in attendances])


@router.post("", response_model=AttendanceResponse)
def create_attendance(
    attendance_data: AttendanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _ensure_attendance_write_access(current_user)
    class_ids = get_accessible_class_ids(current_user, db)
    if attendance_data.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this class.")

    student = db.query(Student).filter(Student.id == attendance_data.student_id).first()
    if not student or student.class_id != attendance_data.class_id:
        raise HTTPException(status_code=400, detail="Student not found in the selected class.")

    if attendance_data.subject_id:
        course = ensure_course_access(attendance_data.subject_id, current_user, db)
        if course.class_id and course.class_id != attendance_data.class_id:
            raise HTTPException(status_code=400, detail="The selected course does not belong to this class.")

    existing = db.query(Attendance).filter(
        Attendance.student_id == attendance_data.student_id,
        Attendance.date == attendance_data.date,
        Attendance.subject_id == attendance_data.subject_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already exists for this date and course.")

    attendance = Attendance(
        student_id=attendance_data.student_id,
        class_id=attendance_data.class_id,
        subject_id=attendance_data.subject_id,
        date=attendance_data.date,
        status=attendance_data.status,
        remark=attendance_data.remark,
    )
    db.add(attendance)
    db.commit()
    db.refresh(attendance)
    return _serialize_attendance(attendance)


@router.put("/{attendance_id}", response_model=AttendanceResponse)
def update_attendance(
    attendance_id: int,
    attendance_data: AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _ensure_attendance_write_access(current_user)
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found.")

    class_ids = get_accessible_class_ids(current_user, db)
    if attendance.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this attendance record.")

    if attendance_data.status is not None:
        attendance.status = attendance_data.status
    if attendance_data.remark is not None:
        attendance.remark = attendance_data.remark

    db.commit()
    db.refresh(attendance)
    return _serialize_attendance(attendance)


@router.delete("/{attendance_id}")
def delete_attendance(
    attendance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _ensure_attendance_write_access(current_user)
    attendance = db.query(Attendance).filter(Attendance.id == attendance_id).first()
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found.")

    class_ids = get_accessible_class_ids(current_user, db)
    if attendance.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this attendance record.")

    db.delete(attendance)
    db.commit()
    return {"message": "Attendance deleted successfully."}


@router.get("/statistics/class/{class_id}")
def get_class_attendance_stats(
    class_id: int,
    subject_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this class.")

    query = db.query(Attendance).filter(Attendance.class_id == class_id)
    if subject_id:
        ensure_course_access(subject_id, current_user, db)
        query = query.filter(Attendance.subject_id == subject_id)
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)

    attendances = query.all()
    stats = {"total": len(attendances), "present": 0, "absent": 0, "late": 0, "leave": 0}
    for attendance in attendances:
        stats[attendance.status] = stats.get(attendance.status, 0) + 1
    stats["attendance_rate"] = round((stats["present"] / stats["total"]) * 100, 2) if stats["total"] else 0
    return stats


@router.post("/batch")
async def create_attendances_batch(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _ensure_attendance_write_access(current_user)
    import json

    body = await request.body()
    body_str = body.decode("utf-8").replace("\x00", "").replace("\ufeff", "")
    try:
        data = json.loads(body_str)
        attendances_list = data.get("attendances", []) if isinstance(data, dict) else data
    except Exception as exc:
        return {"success": 0, "failed": 1, "errors": [f"JSON parse error: {exc}"]}

    if not attendances_list:
        return {"success": 0, "failed": 0, "errors": ["No valid attendance data found."]}

    class_ids = get_accessible_class_ids(current_user, db)
    results = []
    errors = []

    for index, attendance_data in enumerate(attendances_list, 1):
        if not isinstance(attendance_data, dict):
            errors.append(f"Row {index}: invalid record format.")
            continue

        class_id = attendance_data.get("class_id")
        if class_id not in class_ids:
            errors.append(f"Row {index}: no access to the selected class.")
            continue

        student_no = attendance_data.get("student_no")
        if not student_no:
            errors.append(f"Row {index}: missing student number.")
            continue

        student = db.query(Student).filter(Student.student_no == student_no, Student.class_id == class_id).first()
        if not student:
            errors.append(f"Row {index}: student not found in the selected class.")
            continue

        subject_id = attendance_data.get("subject_id")
        if subject_id:
            course = db.query(Subject).filter(Subject.id == subject_id).first()
            if not course:
                errors.append(f"Row {index}: course not found.")
                continue
            if course.class_id and course.class_id != class_id:
                errors.append(f"Row {index}: selected course does not belong to this class.")
                continue

        status = attendance_data.get("status", "present")
        if status not in ["present", "absent", "late", "leave"]:
            errors.append(f"Row {index}: invalid attendance status.")
            continue

        attendance_date = attendance_data.get("date")
        if not attendance_date:
            errors.append(f"Row {index}: missing date.")
            continue
        try:
            if isinstance(attendance_date, str):
                attendance_date = datetime.fromisoformat(attendance_date.replace("Z", "+00:00"))
        except Exception:
            errors.append(f"Row {index}: invalid date format.")
            continue

        existing = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.date == attendance_date,
            Attendance.subject_id == subject_id,
        ).first()
        if existing:
            existing.status = status
            existing.remark = attendance_data.get("remark", "")
        else:
            db.add(
                Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    subject_id=subject_id,
                    date=attendance_date,
                    status=status,
                    remark=attendance_data.get("remark", ""),
                )
            )
        results.append(f"{student.name} {attendance_date.strftime('%Y-%m-%d')}")

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        errors.append(f"Database error: {exc}")

    return {"success": len(results), "failed": len(errors), "errors": errors}


@router.post("/class-batch")
async def create_class_attendance_batch(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _ensure_attendance_write_access(current_user)
    import json

    body = await request.body()
    body_str = body.decode("utf-8").replace("\x00", "").replace("\ufeff", "")

    try:
        data = json.loads(body_str)
    except Exception as exc:
        return {"success": 0, "failed": 1, "errors": [f"JSON parse error: {exc}"]}

    class_id = data.get("class_id")
    subject_id = data.get("subject_id")
    attendance_date = data.get("date")
    status = data.get("status", "present")
    remark = data.get("remark", "")

    if not class_id or not attendance_date:
        return {"success": 0, "failed": 1, "errors": ["Missing class_id or date."]}

    class_ids = get_accessible_class_ids(current_user, db)
    if class_id not in class_ids:
        return {"success": 0, "failed": 1, "errors": ["No access to the selected class."]}

    if subject_id:
        course = db.query(Subject).filter(Subject.id == subject_id).first()
        if not course:
            return {"success": 0, "failed": 1, "errors": ["Course not found."]}
        if course.class_id and course.class_id != class_id:
            return {"success": 0, "failed": 1, "errors": ["Course does not belong to the selected class."]}

    try:
        if isinstance(attendance_date, str):
            attendance_date = datetime.fromisoformat(attendance_date.replace("Z", "+00:00"))
    except Exception:
        return {"success": 0, "failed": 1, "errors": ["Invalid date format."]}

    students = db.query(Student).filter(Student.class_id == class_id).all()
    if not students:
        return {"success": 0, "failed": 1, "errors": ["No students found in this class."]}

    results = []
    for student in students:
        existing = db.query(Attendance).filter(
            Attendance.student_id == student.id,
            Attendance.date == attendance_date,
            Attendance.subject_id == subject_id,
        ).first()
        if existing:
            existing.status = status
            existing.remark = remark
        else:
            db.add(
                Attendance(
                    student_id=student.id,
                    class_id=class_id,
                    subject_id=subject_id,
                    date=attendance_date,
                    status=status,
                    remark=remark,
                )
            )
        results.append(student.name)

    db.commit()
    return {"success": len(results), "failed": 0, "errors": [], "message": f"Updated attendance for {len(results)} students."}


@router.get("/statistics/student/{student_id}")
def get_student_attendance_stats(
    student_id: int,
    subject_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")

    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this student.")

    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    if subject_id:
        ensure_course_access(subject_id, current_user, db)
        query = query.filter(Attendance.subject_id == subject_id)
    if start_date:
        query = query.filter(Attendance.date >= start_date)
    if end_date:
        query = query.filter(Attendance.date <= end_date)

    attendances = query.all()
    stats = {"total": len(attendances), "present": 0, "absent": 0, "late": 0, "leave": 0}
    for attendance in attendances:
        stats[attendance.status] = stats.get(attendance.status, 0) + 1
    stats["attendance_rate"] = round((stats["present"] / stats["total"]) * 100, 2) if stats["total"] else 0
    return stats
