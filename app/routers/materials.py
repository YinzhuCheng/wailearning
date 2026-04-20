from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.attachments import delete_attachment_file_if_unreferenced
from app.course_access import ensure_course_access
from app.database import get_db
from app.models import Class, CourseMaterial, User, UserRole
from app.routers.classes import get_accessible_class_ids
from app.schemas import CourseMaterialCreate, CourseMaterialListResponse, CourseMaterialResponse


router = APIRouter(prefix="/api/materials", tags=["课程资料"])


def can_publish_materials(user: User) -> bool:
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]


def _serialize_material(material: CourseMaterial) -> CourseMaterialResponse:
    return CourseMaterialResponse(
        id=material.id,
        title=material.title,
        content=material.content,
        attachment_name=material.attachment_name,
        attachment_url=material.attachment_url,
        class_id=material.class_id,
        subject_id=material.subject_id,
        created_by=material.created_by,
        created_at=material.created_at,
        updated_at=material.updated_at,
        class_name=material.class_obj.name if material.class_obj else None,
        subject_name=material.subject.name if material.subject else None,
        creator_name=material.creator.real_name if material.creator else None,
    )


@router.get("", response_model=CourseMaterialListResponse)
def get_materials(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = db.query(CourseMaterial)
    allowed_class_ids = get_accessible_class_ids(current_user, db)

    if current_user.role != UserRole.ADMIN:
        if not allowed_class_ids:
            return CourseMaterialListResponse(total=0, data=[])
        query = query.filter(CourseMaterial.class_id.in_(allowed_class_ids))

    if class_id:
        if current_user.role != UserRole.ADMIN and class_id not in allowed_class_ids:
            return CourseMaterialListResponse(total=0, data=[])
        query = query.filter(CourseMaterial.class_id == class_id)

    if subject_id:
        ensure_course_access(subject_id, current_user, db)
        query = query.filter(CourseMaterial.subject_id == subject_id)

    total = query.count()
    materials = query.order_by(desc(CourseMaterial.created_at)).offset((page - 1) * page_size).limit(page_size).all()
    return CourseMaterialListResponse(total=total, data=[_serialize_material(item) for item in materials])


@router.get("/{material_id}", response_model=CourseMaterialResponse)
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found.")

    allowed_class_ids = get_accessible_class_ids(current_user, db)
    if current_user.role != UserRole.ADMIN and material.class_id not in allowed_class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this material.")

    if material.subject_id:
        ensure_course_access(material.subject_id, current_user, db)

    return _serialize_material(material)


@router.post("", response_model=CourseMaterialResponse)
def create_material(
    data: CourseMaterialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not can_publish_materials(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can publish materials.")

    allowed_class_ids = get_accessible_class_ids(current_user, db)
    if current_user.role != UserRole.ADMIN and data.class_id not in allowed_class_ids:
        raise HTTPException(status_code=403, detail="You do not have access to this class.")

    class_obj = db.query(Class).filter(Class.id == data.class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found.")

    if data.subject_id:
        course = ensure_course_access(data.subject_id, current_user, db)
        if course.class_id and course.class_id != data.class_id:
            raise HTTPException(status_code=400, detail="The selected course does not belong to this class.")

    material = CourseMaterial(
        title=data.title,
        content=data.content,
        attachment_name=data.attachment_name,
        attachment_url=data.attachment_url,
        class_id=data.class_id,
        subject_id=data.subject_id,
        created_by=current_user.id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return _serialize_material(material)


@router.delete("/{material_id}")
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not can_publish_materials(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can delete materials.")

    material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found.")

    if current_user.role != UserRole.ADMIN and material.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own materials.")

    db.delete(material)
    db.flush()
    delete_attachment_file_if_unreferenced(db, material.attachment_url)
    db.commit()
    return {"message": "Material deleted successfully."}
