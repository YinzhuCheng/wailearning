import re
from typing import Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.attachments import delete_attachment_file_if_unreferenced
from app.auth import get_current_active_user
from app.course_access import prepare_student_course_context, sync_student_course_enrollments
from app.database import get_db
from app.models import (
    Attendance,
    Class,
    CourseEnrollment,
    Gender,
    HomeworkAttempt,
    HomeworkGradingTask,
    HomeworkScoreCandidate,
    HomeworkSubmission,
    LLMTokenUsageLog,
    Score,
    Student,
    User,
    UserRole,
)
from app.routers.classes import apply_class_id_filter, get_accessible_class_ids
from app.schemas import StudentCreate, StudentListResponse, StudentResponse, StudentUpdate
from app.student_user_sync import sync_student_user_from_roster_row


router = APIRouter(prefix="/api/students", tags=["学生管理"])


FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")
CHINESE_DIGITS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


class BatchStudentItem(BaseModel):
    name: str
    student_no: str
    gender: Optional[str] = None
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    phone: Optional[str] = None
    parent_phone: Optional[str] = None
    address: Optional[str] = None


class BatchStudentImportRequest(BaseModel):
    students: List[BatchStudentItem]


def build_student_response(
    student: Student,
    *,
    class_name: Optional[str] = None,
    has_user: bool = False,
) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        name=student.name,
        student_no=student.student_no,
        gender=student.gender,
        phone=student.phone,
        parent_phone=student.parent_phone,
        address=student.address,
        class_id=student.class_id,
        teacher_id=student.teacher_id,
        created_at=student.created_at,
        class_name=class_name,
        parent_code=student.parent_code,
        has_user=has_user,
    )


def clean_text(value: Optional[object]) -> str:
    if value is None:
        return ""
    return str(value).strip()


def serialize_students(students: List[Student], db: Session) -> List[StudentResponse]:
    if not students:
        return []

    class_ids = {student.class_id for student in students if student.class_id is not None}
    student_nos = {
        clean_text(student.student_no)
        for student in students
        if clean_text(student.student_no)
    }

    class_map = {}
    if class_ids:
        class_rows = db.query(Class.id, Class.name).filter(Class.id.in_(class_ids)).all()
        class_map = {class_id: class_name for class_id, class_name in class_rows}

    existing_usernames = set()
    if student_nos:
        existing_usernames = {
            username
            for (username,) in db.query(User.username).filter(User.username.in_(student_nos)).all()
        }

    return [
        build_student_response(
            student,
            class_name=class_map.get(student.class_id),
            has_user=clean_text(student.student_no) in existing_usernames,
        )
        for student in students
    ]


def normalize_gender(value: object) -> Gender:
    gender_text = clean_text(value).translate(FULLWIDTH_DIGITS).lower()
    gender_mapping = {
        "男": Gender.MALE,
        "male": Gender.MALE,
        "m": Gender.MALE,
        "1": Gender.MALE,
        "男性": Gender.MALE,
        "女": Gender.FEMALE,
        "female": Gender.FEMALE,
        "f": Gender.FEMALE,
        "0": Gender.FEMALE,
        "女性": Gender.FEMALE,
    }
    gender = gender_mapping.get(gender_text)
    if gender is None:
        raise ValueError("性别仅支持 男 / 女")
    return gender


def parse_chinese_number(value: str) -> Optional[int]:
    if not value:
        return None

    if value in CHINESE_DIGITS:
        return CHINESE_DIGITS[value]

    if value.startswith("十"):
        tail = value[1:]
        return 10 if not tail else 10 + CHINESE_DIGITS.get(tail, 0)

    if value.endswith("十"):
        head = CHINESE_DIGITS.get(value[0])
        return None if head is None else head * 10

    if "十" in value:
        head, tail = value.split("十", 1)
        head_value = CHINESE_DIGITS.get(head)
        tail_value = CHINESE_DIGITS.get(tail)
        if head_value is None or tail_value is None:
            return None
        return head_value * 10 + tail_value

    return None


def derive_grade_from_class_name(class_name: str, db: Session) -> int:
    normalized_name = class_name.translate(FULLWIDTH_DIGITS)

    grade_match = re.search(r"(\d+)\s*年级", normalized_name)
    if grade_match:
        grade = int(grade_match.group(1))
        if 1 <= grade <= 12:
            return grade

    level_match = re.search(r"(\d+)\s*级", normalized_name)
    if level_match:
        grade = int(level_match.group(1))
        if 1 <= grade <= 12:
            return grade

    chinese_grade_match = re.search(r"([一二三四五六七八九十]{1,3})\s*年级", class_name)
    if chinese_grade_match:
        grade = parse_chinese_number(chinese_grade_match.group(1))
        if grade and 1 <= grade <= 12:
            return grade

    stage_patterns = (
        (r"小([一二三四五六1-6])", 0),
        (r"初([一二三1-3])", 6),
        (r"高([一二三1-3])", 9),
    )
    for pattern, offset in stage_patterns:
        stage_match = re.search(pattern, class_name)
        if not stage_match:
            continue

        token = stage_match.group(1)
        if token.isdigit():
            return offset + int(token)

        grade = parse_chinese_number(token)
        if grade:
            return offset + grade

    max_grade_row = db.query(Class.grade).order_by(Class.grade.desc()).first()
    return max_grade_row[0] if max_grade_row else 1


def resolve_import_class(
    row: BatchStudentItem,
    db: Session,
    current_user: User,
    accessible_class_ids: Set[int],
    class_cache: Dict[str, Class],
    created_classes: List[str],
) -> Class:
    is_admin = current_user.role == UserRole.ADMIN.value

    if row.class_id is not None:
        class_obj = db.query(Class).filter(Class.id == row.class_id).first()
        if not class_obj:
            raise ValueError("所属班级不存在")
        if not is_admin and class_obj.id not in accessible_class_ids:
            raise PermissionError("无权在该班级导入学生")
        class_cache.setdefault(class_obj.name, class_obj)
        return class_obj

    class_name = clean_text(row.class_name)
    if not class_name:
        raise ValueError("所属班级不能为空")

    cached_class = class_cache.get(class_name)
    if cached_class:
        return cached_class

    class_obj = db.query(Class).filter(Class.name == class_name).order_by(Class.id.asc()).first()
    if class_obj:
        if not is_admin and class_obj.id not in accessible_class_ids:
            raise PermissionError("无权在该班级导入学生")
        class_cache[class_name] = class_obj
        return class_obj

    if not is_admin:
        raise PermissionError("所属班级不存在，当前账号无法自动创建班级")

    class_obj = Class(name=class_name, grade=derive_grade_from_class_name(class_name, db))
    db.add(class_obj)
    db.flush()
    class_cache[class_name] = class_obj
    created_classes.append(class_name)
    return class_obj


@router.get("", response_model=StudentListResponse)
def get_students(
    class_id: Optional[int] = None,
    name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    class_ids = get_accessible_class_ids(current_user, db)
    query = apply_class_id_filter(db.query(Student), Student.class_id, class_ids)

    if class_id:
        if class_id not in class_ids:
            raise HTTPException(status_code=403, detail="无权访问该班级")
        query = query.filter(Student.class_id == class_id)

    if name:
        query = query.filter(Student.name.contains(name))

    total = query.count()
    students = query.offset((page - 1) * page_size).limit(page_size).all()

    return StudentListResponse(
        total=total,
        data=serialize_students(students, db),
    )


@router.post("", response_model=StudentResponse)
def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    class_ids = get_accessible_class_ids(current_user, db)
    if student_data.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权在该班级添加学生")

    existing = db.query(Student).filter(
        Student.student_no == student_data.student_no,
        Student.class_id == student_data.class_id,
    ).first()
    if existing:
        if (existing.name or "").strip() != (student_data.name or "").strip():
            raise HTTPException(status_code=400, detail="该班级中学号已存在")
        # Idempotent: same class + student_no and same display name (e.g. roster sync).
        existing.name = student_data.name
        existing.gender = student_data.gender
        existing.phone = student_data.phone
        existing.parent_phone = student_data.parent_phone
        existing.address = student_data.address
        if current_user.role == UserRole.TEACHER.value and existing.teacher_id is None:
            existing.teacher_id = current_user.id
        db.flush()
        sync_student_course_enrollments(existing, db)
        sync_student_user_from_roster_row(db, existing)
        linked = db.query(User).filter(User.username == existing.student_no).first()
        if linked and linked.role == UserRole.STUDENT.value:
            prepare_student_course_context(linked, db)
        db.commit()
        db.refresh(existing)
        return serialize_students([existing], db)[0]

    student = Student(
        name=student_data.name,
        student_no=student_data.student_no,
        gender=student_data.gender,
        phone=student_data.phone,
        parent_phone=student_data.parent_phone,
        address=student_data.address,
        class_id=student_data.class_id,
        teacher_id=current_user.id if current_user.role == UserRole.TEACHER.value else None,
    )
    db.add(student)
    db.flush()
    sync_student_course_enrollments(student, db)
    sync_student_user_from_roster_row(db, student)
    db.commit()
    db.refresh(student)

    return serialize_students([student], db)[0]


@router.post("/batch")
def create_students_batch(
    payload: BatchStudentImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not payload.students:
        return {
            "success": 0,
            "failed": 0,
            "total": 0,
            "duplicate": 0,
            "names": [],
            "errors": [],
            "failed_data": [],
            "created_classes": [],
        }

    accessible_class_ids = set(get_accessible_class_ids(current_user, db))
    class_cache: Dict[str, Class] = {}
    created_classes: List[str] = []
    errors: List[str] = []
    failed_data: List[dict] = []
    success_names: List[str] = []
    duplicate_count = 0
    new_students: List[Student] = []
    seen_student_keys: Set[Tuple[int, str]] = set()

    for index, row in enumerate(payload.students, start=1):
        row_number = index + 1
        name = clean_text(row.name)
        student_no = clean_text(row.student_no)

        if not name:
            message = f"第 {row_number} 行缺少姓名"
            errors.append(message)
            failed_data.append({"row": row_number, "name": "", "student_no": student_no, "error": "缺少姓名"})
            continue

        if not student_no:
            message = f"第 {row_number} 行缺少学号"
            errors.append(message)
            failed_data.append({"row": row_number, "name": name, "student_no": "", "error": "缺少学号"})
            continue

        try:
            raw_gender = clean_text(row.gender)
            if not raw_gender:
                gender = Gender.MALE
            else:
                gender = normalize_gender(raw_gender)
        except ValueError as exc:
            message = f"第 {row_number} 行性别格式不正确"
            errors.append(message)
            failed_data.append({"row": row_number, "name": name, "student_no": student_no, "error": str(exc)})
            continue

        try:
            class_obj = resolve_import_class(
                row=row,
                db=db,
                current_user=current_user,
                accessible_class_ids=accessible_class_ids,
                class_cache=class_cache,
                created_classes=created_classes,
            )
        except PermissionError as exc:
            errors.append(f"第 {row_number} 行{exc}")
            failed_data.append({"row": row_number, "name": name, "student_no": student_no, "error": str(exc)})
            continue
        except ValueError as exc:
            errors.append(f"第 {row_number} 行{exc}")
            failed_data.append({"row": row_number, "name": name, "student_no": student_no, "error": str(exc)})
            continue

        student_key = (class_obj.id, student_no)
        if student_key in seen_student_keys:
            duplicate_count += 1
            message = f"第 {row_number} 行学号 {student_no} 在导入文件中重复"
            errors.append(message)
            failed_data.append({"row": row_number, "name": name, "student_no": student_no, "error": "导入文件内重复学号"})
            continue

        existing_student = db.query(Student).filter(
            Student.student_no == student_no,
            Student.class_id == class_obj.id,
        ).first()
        if existing_student:
            duplicate_count += 1
            message = f"第 {row_number} 行学号 {student_no} 在班级 {class_obj.name} 中已存在"
            errors.append(message)
            failed_data.append({"row": row_number, "name": name, "student_no": student_no, "error": "该班级中学号已存在"})
            continue

        student = Student(
            name=name,
            student_no=student_no,
            gender=gender,
            phone=clean_text(row.phone) or None,
            parent_phone=clean_text(row.parent_phone) or None,
            address=clean_text(row.address) or None,
            class_id=class_obj.id,
            teacher_id=current_user.id if current_user.role == UserRole.TEACHER.value else None,
        )
        db.add(student)
        new_students.append(student)
        seen_student_keys.add(student_key)
        success_names.append(name)

    try:
        db.flush()
        for student in new_students:
            sync_student_course_enrollments(student, db)
            sync_student_user_from_roster_row(db, student)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"批量导入失败：{exc}") from exc

    return {
        "success": len(success_names),
        "failed": len(errors),
        "total": len(payload.students),
        "duplicate": duplicate_count,
        "names": success_names,
        "errors": errors,
        "failed_data": failed_data,
        "created_classes": created_classes,
    }


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该学生")

    return serialize_students([student], db)[0]


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student_data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权修改该学生")

    if student_data.name is not None:
        student.name = student_data.name

    if student_data.student_no is not None:
        target_class_id = student_data.class_id if student_data.class_id is not None else student.class_id
        existing = db.query(Student).filter(
            Student.student_no == student_data.student_no,
            Student.class_id == target_class_id,
            Student.id != student_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="该班级中学号已存在")
        student.student_no = student_data.student_no

    if student_data.gender is not None:
        student.gender = student_data.gender
    if student_data.phone is not None:
        student.phone = student_data.phone
    if student_data.parent_phone is not None:
        student.parent_phone = student_data.parent_phone
    if student_data.address is not None:
        student.address = student_data.address

    class_changed = False
    if student_data.class_id is not None:
        if student_data.class_id not in class_ids:
            raise HTTPException(status_code=403, detail="无权移动到该班级")
        class_changed = student.class_id != student_data.class_id
        student.class_id = student_data.class_id

    if class_changed:
        db.query(CourseEnrollment).filter(CourseEnrollment.student_id == student.id).delete()
        db.flush()
        sync_student_course_enrollments(student, db)

    sync_student_user_from_roster_row(db, student)

    db.commit()
    db.refresh(student)

    return serialize_students([student], db)[0]


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权删除该学生")

    try:
        db.query(CourseEnrollment).filter(CourseEnrollment.student_id == student_id).delete()
        submissions = db.query(HomeworkSubmission).filter(HomeworkSubmission.student_id == student_id).all()
        attempts = db.query(HomeworkAttempt).filter(HomeworkAttempt.student_id == student_id).all()
        for attempt in attempts:
            db.query(HomeworkScoreCandidate).filter(HomeworkScoreCandidate.attempt_id == attempt.id).delete()
            task_ids = [
                item.id
                for item in db.query(HomeworkGradingTask.id).filter(HomeworkGradingTask.attempt_id == attempt.id).all()
            ]
            if task_ids:
                db.query(LLMTokenUsageLog).filter(LLMTokenUsageLog.task_id.in_(task_ids)).delete(
                    synchronize_session=False
                )
            db.query(HomeworkGradingTask).filter(HomeworkGradingTask.attempt_id == attempt.id).delete()
            delete_attachment_file_if_unreferenced(db, attempt.attachment_url)
            db.delete(attempt)
        for submission in submissions:
            delete_attachment_file_if_unreferenced(db, submission.attachment_url)
            db.delete(submission)
        db.query(Attendance).filter(Attendance.student_id == student_id).delete()
        db.query(Score).filter(Score.student_id == student_id).delete()
        db.delete(student)
        db.commit()
        return {"message": "学生删除成功"}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除学生失败: {exc}") from exc
