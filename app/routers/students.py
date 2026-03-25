from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models import User, Student, Class
from app.schemas import StudentCreate, StudentUpdate, StudentResponse, StudentListResponse
from app.auth import get_current_active_user
from app.routers.classes import get_accessible_class_ids

router = APIRouter(prefix="/api/students", tags=["学生管理"])

@router.get("", response_model=StudentListResponse)
def get_students(
    class_id: Optional[int] = None,
    name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    class_ids = get_accessible_class_ids(current_user, db)
    
    query = db.query(Student).filter(Student.class_id.in_(class_ids))
    
    if class_id:
        if class_id not in class_ids:
            raise HTTPException(status_code=403, detail="无权访问该班级")
        query = query.filter(Student.class_id == class_id)
    
    if name:
        query = query.filter(Student.name.contains(name))
    
    total = query.count()
    students = query.offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for s in students:
        class_obj = db.query(Class).filter(Class.id == s.class_id).first()
        result.append(StudentResponse(
            id=s.id,
            name=s.name,
            student_no=s.student_no,
            gender=s.gender,
            phone=s.phone,
            parent_phone=s.parent_phone,
            address=s.address,
            class_id=s.class_id,
            teacher_id=s.teacher_id,
            created_at=s.created_at,
            class_name=class_obj.name if class_obj else None
        ))
    
    return StudentListResponse(total=total, data=result)

@router.post("", response_model=StudentResponse)
def create_student(
    student_data: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    class_ids = get_accessible_class_ids(current_user, db)
    if student_data.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权在该班级添加学生")
    
    existing = db.query(Student).filter(
        Student.student_no == student_data.student_no,
        Student.class_id == student_data.class_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该班级中学号已存在")
    
    student = Student(
        name=student_data.name,
        student_no=student_data.student_no,
        gender=student_data.gender,
        phone=student_data.phone,
        parent_phone=student_data.parent_phone,
        address=student_data.address,
        class_id=student_data.class_id,
        teacher_id=current_user.id if current_user.role == "teacher" else None
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    
    class_obj = db.query(Class).filter(Class.id == student.class_id).first()
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
        class_name=class_obj.name if class_obj else None
    )

@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权访问该学生")
    
    class_obj = db.query(Class).filter(Class.id == student.class_id).first()
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
        class_name=class_obj.name if class_obj else None
    )

@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    student_data: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
            Student.id != student_id
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
    if student_data.class_id is not None:
        if student_data.class_id not in class_ids:
            raise HTTPException(status_code=403, detail="无权移动到该班级")
        student.class_id = student_data.class_id
    
    db.commit()
    db.refresh(student)
    
    class_obj = db.query(Class).filter(Class.id == student.class_id).first()
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
        class_name=class_obj.name if class_obj else None
    )

@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    
    class_ids = get_accessible_class_ids(current_user, db)
    if student.class_id not in class_ids:
        raise HTTPException(status_code=403, detail="无权删除该学生")
    
    db.delete(student)
    db.commit()
    return {"message": "学生删除成功"}

from fastapi import Request
from urllib.parse import parse_qs
import re

@router.post("/batch")
async def create_students_batch(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    import json
    import sys
    print(f"[DEBUG] 批量导入请求开始 - 用户ID: {current_user.id}, 用户名: {current_user.username}, 角色: {current_user.role}, 用户class_id: {current_user.class_id}", file=sys.stderr)
    
    body = await request.body()
    
    def detect_and_decode(data: bytes) -> str:
        try:
            content = data.decode('utf-8')
            content = content.replace('\x00', '').replace('\ufeff', '')
            
            if '\ufffd' in content or contains_garbled_chars(content):
                print(f"[DEBUG] UTF-8解码后检测到可能的乱码，尝试GBK解码", file=sys.stderr)
                gbk_content = data.decode('gbk', errors='ignore')
                gbk_content = gbk_content.replace('\x00', '').replace('\ufeff', '')
                
                if is_valid_chinese(gbk_content) and not contains_garbled_chars(gbk_content):
                    print(f"[DEBUG] 使用GBK编码成功解码", file=sys.stderr)
                    return gbk_content
            
            return content
        except UnicodeDecodeError:
            print(f"[DEBUG] UTF-8解码失败，尝试GBK解码", file=sys.stderr)
            return data.decode('gbk', errors='ignore')
    
    def contains_garbled_chars(text: str) -> bool:
        if '\ufffd' in text:
            return True
        garbled_patterns = ['锟斤拷', '烫烫烫', '?', '�']
        for pattern in garbled_patterns:
            if pattern in text:
                return True
        return False
    
    def is_valid_chinese(text: str) -> bool:
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
        return len(chinese_chars) > 0
    
    body_str = detect_and_decode(body)
    
    students_list = []
    errors_list = []
    
    try:
        data = json.loads(body_str)
        if isinstance(data, dict) and "students" in data:
            students_list = data.get("students", [])
        elif isinstance(data, list):
            students_list = data
        print(f"[DEBUG] 解析到学生数据数量: {len(students_list)}", file=sys.stderr)
        if students_list:
            print(f"[DEBUG] 第一个学生数据: {students_list[0]}", file=sys.stderr)
    except Exception as e:
        errors_list.append(f"JSON解析错误: {str(e)}")
        print(f"[DEBUG] JSON解析错误: {str(e)}", file=sys.stderr)
        print(f"[DEBUG] 请求体内容: {body_str[:500]}", file=sys.stderr)
    
    if not students_list:
        print(f"[DEBUG] 没有有效的学生数据", file=sys.stderr)
        return {
            "success": 0,
            "failed": 0,
            "names": [],
            "errors": ["没有有效的学生数据"]
        }
    
    class_ids = get_accessible_class_ids(current_user, db)
    print(f"[DEBUG] 当前用户可访问的班级ID列表: {class_ids}", file=sys.stderr)
    
    results = []
    errors = []
    failed_data = []
    duplicate_count = 0
    
    for i, student_data in enumerate(students_list):
        if not isinstance(student_data, dict):
            error_msg = f"第{i+1}行: 数据格式错误"
            errors.append(error_msg)
            failed_data.append({
                "row": i + 1,
                "name": student_data.get("name", ""),
                "student_no": student_data.get("student_no", ""),
                "error": "数据格式错误"
            })
            continue
            
        class_id = student_data.get("class_id")
        print(f"[DEBUG] 第{i+1}个学生 - class_id原始值: {class_id}, 类型: {type(class_id)}", file=sys.stderr)
        
        try:
            class_id = int(class_id)
            print(f"[DEBUG] 转换后class_id: {class_id}", file=sys.stderr)
        except (ValueError, TypeError) as e:
            error_msg = f"第{i+1}行: 班级ID格式错误"
            errors.append(error_msg)
            failed_data.append({
                "row": i + 1,
                "name": student_data.get("name", ""),
                "student_no": student_data.get("student_no", ""),
                "error": "班级ID格式错误"
            })
            print(f"[DEBUG] 班级ID转换错误: {e}", file=sys.stderr)
            continue
        
        if class_id not in class_ids:
            error_msg = f"第{i+1}行: 无权在该班级添加学生 (班级ID: {class_id})"
            errors.append(error_msg)
            failed_data.append({
                "row": i + 1,
                "name": student_data.get("name", ""),
                "student_no": student_data.get("student_no", ""),
                "error": "无权在该班级添加学生"
            })
            print(f"[DEBUG] 无权访问班级 {class_id}", file=sys.stderr)
            continue
        
        existing_in_class = db.query(Student).filter(
            Student.student_no == student_data.get("student_no"),
            Student.class_id == class_id
        ).first()
        if existing_in_class:
            error_msg = f"第{i+1}行: 学号 {student_data.get('student_no')} 在该班级已存在"
            errors.append(error_msg)
            duplicate_count += 1
            failed_data.append({
                "row": i + 1,
                "name": student_data.get("name", ""),
                "student_no": student_data.get("student_no", ""),
                "error": "学号已存在"
            })
            continue
        
        student = Student(
            name=student_data.get("name", ""),
            student_no=student_data.get("student_no", ""),
            gender=student_data.get("gender", "male"),
            phone=student_data.get("phone", ""),
            parent_phone=student_data.get("parent_phone", ""),
            address=student_data.get("address", ""),
            class_id=class_id,
            teacher_id=current_user.id if current_user.role == "teacher" else None
        )
        db.add(student)
        results.append(student_data.get("name", ""))
        print(f"[DEBUG] 成功添加学生: {student_data.get('name')} 到班级 {class_id}", file=sys.stderr)
    
    try:
        db.commit()
        print(f"[DEBUG] 批量导入完成 - 成功: {len(results)}, 失败: {len(errors)}, 重复: {duplicate_count}", file=sys.stderr)
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        print(f"[DEBUG] 数据库提交失败: {error_msg}", file=sys.stderr)
        if "duplicate key" in error_msg.lower() or "unique" in error_msg.lower():
            errors.append(f"数据库错误: 部分学号在该班级可能已存在")
            return {
                "success": len(results),
                "failed": len(errors) + 1,
                "total": len(students_list),
                "duplicate": duplicate_count,
                "names": results,
                "errors": errors,
                "failed_data": failed_data
            }
        else:
            raise e
    
    return {
        "success": len(results),
        "failed": len(errors),
        "total": len(students_list),
        "duplicate": duplicate_count,
        "names": results,
        "errors": errors,
        "failed_data": failed_data
    }
