from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.course_access import ensure_course_access_http, is_course_instructor
from app.database import get_db
from app.models import CourseMaterial, CourseMaterialChapter, CourseMaterialSection, Subject, User
from app.schemas import (
    CourseMaterialAddPlacementRequest,
    CourseMaterialChapterCreate,
    CourseMaterialChapterNode,
    CourseMaterialChapterReorderRequest,
    CourseMaterialChapterTreeResponse,
    CourseMaterialChapterUpdate,
    CourseMaterialSectionReorderRequest,
)
from app.services import LogService

router = APIRouter(prefix="/api/material-chapters", tags=["资料章节"])


def _ensure_instructor(user: User, course: Subject) -> None:
    if not is_course_instructor(user, course):
        raise HTTPException(status_code=403, detail="Only the assigned course instructor may manage chapters.")


def _chapter_belongs_to_subject(chapter: CourseMaterialChapter, subject_id: int) -> bool:
    return int(chapter.subject_id) == int(subject_id)


def _build_tree_rows(subject_id: int, db: Session) -> List[CourseMaterialChapterNode]:
    chapters = (
        db.query(CourseMaterialChapter)
        .filter(CourseMaterialChapter.subject_id == subject_id)
        .order_by(CourseMaterialChapter.sort_order.asc(), CourseMaterialChapter.id.asc())
        .all()
    )
    by_parent: dict[Optional[int], List[CourseMaterialChapter]] = {}
    for ch in chapters:
        by_parent.setdefault(ch.parent_id, []).append(ch)

    def build(pid: Optional[int]) -> List[CourseMaterialChapterNode]:
        nodes: List[CourseMaterialChapterNode] = []
        for ch in by_parent.get(pid, []):
            nodes.append(
                CourseMaterialChapterNode(
                    id=ch.id,
                    subject_id=ch.subject_id,
                    parent_id=ch.parent_id,
                    title=ch.title,
                    sort_order=ch.sort_order,
                    is_uncategorized=bool(ch.is_uncategorized),
                    children=build(ch.id),
                )
            )
        return nodes

    return build(None)


@router.get("/tree", response_model=CourseMaterialChapterTreeResponse)
def get_chapter_tree(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = ensure_course_access_http(subject_id, current_user, db)
    _ = course
    nodes = _build_tree_rows(subject_id, db)
    return CourseMaterialChapterTreeResponse(nodes=nodes)


@router.post("", response_model=CourseMaterialChapterNode)
def create_chapter(
    subject_id: int,
    data: CourseMaterialChapterCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = ensure_course_access_http(subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    parent_id = data.parent_id
    if parent_id is not None:
        parent = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == parent_id).first()
        if not parent or not _chapter_belongs_to_subject(parent, subject_id):
            raise HTTPException(status_code=400, detail="Invalid parent chapter.")
        if parent.is_uncategorized:
            raise HTTPException(status_code=400, detail="Cannot nest under uncategorized bucket.")

    sort_order = data.sort_order
    if sort_order is None:
        sort_order = (
            db.query(CourseMaterialChapter)
            .filter(
                CourseMaterialChapter.subject_id == subject_id,
                CourseMaterialChapter.parent_id == parent_id,
            )
            .count()
        )

    chapter = CourseMaterialChapter(
        subject_id=subject_id,
        parent_id=parent_id,
        title=data.title.strip(),
        sort_order=int(sort_order),
        is_uncategorized=False,
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)

    LogService.log_create(
        db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="资料章节",
        target_id=chapter.id,
        target_name=chapter.title,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return CourseMaterialChapterNode(
        id=chapter.id,
        subject_id=chapter.subject_id,
        parent_id=chapter.parent_id,
        title=chapter.title,
        sort_order=chapter.sort_order,
        is_uncategorized=False,
        children=[],
    )


@router.put("/{chapter_id}", response_model=CourseMaterialChapterNode)
def update_chapter(
    chapter_id: int,
    data: CourseMaterialChapterUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    chapter = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found.")

    course = ensure_course_access_http(chapter.subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    if chapter.is_uncategorized and data.title is not None:
        raise HTTPException(status_code=400, detail="Cannot rename the uncategorized bucket.")

    old_title = chapter.title
    if data.title is not None:
        chapter.title = data.title.strip()
    db.commit()
    db.refresh(chapter)

    LogService.log_update(
        db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="资料章节",
        target_id=chapter.id,
        target_name=chapter.title,
        changes=f"标题 {old_title} -> {chapter.title}" if data.title is not None else None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return CourseMaterialChapterNode(
        id=chapter.id,
        subject_id=chapter.subject_id,
        parent_id=chapter.parent_id,
        title=chapter.title,
        sort_order=chapter.sort_order,
        is_uncategorized=bool(chapter.is_uncategorized),
        children=[],
    )


@router.delete("/{chapter_id}")
def delete_chapter(
    chapter_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    chapter = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found.")
    if chapter.is_uncategorized:
        raise HTTPException(status_code=400, detail="Cannot delete the uncategorized bucket.")

    course = ensure_course_access_http(chapter.subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    unc = (
        db.query(CourseMaterialChapter)
        .filter(
            CourseMaterialChapter.subject_id == chapter.subject_id,
            CourseMaterialChapter.is_uncategorized.is_(True),
        )
        .first()
    )
    if not unc:
        raise HTTPException(status_code=500, detail="Uncategorized chapter missing.")

    # Move sections to uncategorized (preserve material rows)
    sections = db.query(CourseMaterialSection).filter(CourseMaterialSection.chapter_id == chapter_id).all()
    for sec in sections:
        dup = (
            db.query(CourseMaterialSection)
            .filter(
                CourseMaterialSection.material_id == sec.material_id,
                CourseMaterialSection.chapter_id == unc.id,
            )
            .first()
        )
        if dup:
            db.delete(sec)
        else:
            sec.chapter_id = unc.id

    children = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.parent_id == chapter_id).all()
    for child in children:
        child.parent_id = chapter.parent_id

    title_saved = chapter.title
    subject_saved = chapter.subject_id
    db.delete(chapter)
    db.commit()

    LogService.log_delete(
        db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="资料章节",
        target_id=chapter_id,
        target_name=title_saved,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"message": "Chapter deleted.", "subject_id": subject_saved}


@router.post("/reorder")
def reorder_chapters(
    subject_id: int,
    payload: CourseMaterialChapterReorderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = ensure_course_access_http(subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    parent_id = payload.parent_id
    for idx, cid in enumerate(payload.ordered_chapter_ids):
        ch = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == cid).first()
        if not ch or not _chapter_belongs_to_subject(ch, subject_id):
            raise HTTPException(status_code=400, detail="Invalid chapter in list.")
        if ch.parent_id != parent_id:
            raise HTTPException(status_code=400, detail="Chapter parent mismatch.")
        if ch.is_uncategorized:
            raise HTTPException(status_code=400, detail="Cannot reorder uncategorized via this endpoint.")
        ch.sort_order = idx
    db.commit()

    LogService.log(
        db=db,
        action="修改",
        target_type="资料章节",
        user_id=current_user.id,
        username=current_user.username,
        target_id=subject_id,
        target_name=course.name,
        details="调整章节顺序",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"message": "Order updated."}


@router.post("/sections/reorder")
def reorder_sections(
    subject_id: int,
    payload: CourseMaterialSectionReorderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = ensure_course_access_http(subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    chapter = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == payload.chapter_id).first()
    if not chapter or not _chapter_belongs_to_subject(chapter, subject_id):
        raise HTTPException(status_code=404, detail="Chapter not found.")

    id_set = set(payload.ordered_section_ids)
    existing = (
        db.query(CourseMaterialSection)
        .filter(CourseMaterialSection.chapter_id == payload.chapter_id)
        .all()
    )
    if len(id_set) != len(existing) or id_set != {s.id for s in existing}:
        raise HTTPException(status_code=400, detail="Section list must match chapter contents.")

    for idx, sid in enumerate(payload.ordered_section_ids):
        sec = db.query(CourseMaterialSection).filter(CourseMaterialSection.id == sid).first()
        if sec:
            sec.sort_order = idx
    db.commit()

    LogService.log(
        db=db,
        action="修改",
        target_type="课程资料排序",
        user_id=current_user.id,
        username=current_user.username,
        target_id=payload.chapter_id,
        target_name=chapter.title,
        details="调整资料在章节内的顺序",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"message": "Section order updated."}


@router.post("/materials/{material_id}/placements", response_model=dict)
def add_material_placement(
    material_id: int,
    subject_id: int,
    payload: CourseMaterialAddPlacementRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = ensure_course_access_http(subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    material = db.query(CourseMaterial).filter(CourseMaterial.id == material_id).first()
    if not material or material.subject_id != subject_id:
        raise HTTPException(status_code=404, detail="Material not found for this course.")

    chapter = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == payload.chapter_id).first()
    if not chapter or not _chapter_belongs_to_subject(chapter, subject_id):
        raise HTTPException(status_code=404, detail="Chapter not found.")

    exists = (
        db.query(CourseMaterialSection)
        .filter(
            CourseMaterialSection.material_id == material_id,
            CourseMaterialSection.chapter_id == payload.chapter_id,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Material already in this chapter.")

    max_so = (
        db.query(CourseMaterialSection)
        .filter(CourseMaterialSection.chapter_id == payload.chapter_id)
        .count()
    )
    sec = CourseMaterialSection(
        material_id=material_id,
        chapter_id=payload.chapter_id,
        sort_order=max_so,
    )
    db.add(sec)
    db.commit()
    db.refresh(sec)

    LogService.log_create(
        db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="课程资料引用",
        target_id=sec.id,
        target_name=f"{material.title} → {chapter.title}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"section_id": sec.id, "chapter_id": chapter.id}


@router.delete("/placements/{section_id}")
def remove_material_placement(
    section_id: int,
    subject_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    course = ensure_course_access_http(subject_id, current_user, db)
    _ensure_instructor(current_user, course)

    sec = db.query(CourseMaterialSection).filter(CourseMaterialSection.id == section_id).first()
    if not sec:
        raise HTTPException(status_code=404, detail="Placement not found.")

    chapter = db.query(CourseMaterialChapter).filter(CourseMaterialChapter.id == sec.chapter_id).first()
    if not chapter or not _chapter_belongs_to_subject(chapter, subject_id):
        raise HTTPException(status_code=403, detail="Invalid placement.")

    if chapter.is_uncategorized:
        others = (
            db.query(CourseMaterialSection)
            .filter(CourseMaterialSection.material_id == sec.material_id)
            .count()
        )
        if others <= 1:
            raise HTTPException(status_code=400, detail="Material must remain in at least one chapter.")

    material = db.query(CourseMaterial).filter(CourseMaterial.id == sec.material_id).first()
    label = f"{material.title if material else ''} ← {chapter.title}"
    db.delete(sec)
    db.commit()

    LogService.log_delete(
        db,
        user_id=current_user.id,
        username=current_user.username,
        target_type="课程资料引用",
        target_id=section_id,
        target_name=label,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return {"message": "Placement removed."}
