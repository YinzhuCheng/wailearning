from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_active_user
from app.course_access import ensure_course_access
from app.database import get_db
from app.llm_grading import ensure_course_llm_config, validate_endpoint_connectivity
from app.models import (
    CourseLLMConfig,
    CourseLLMConfigEndpoint,
    LLMEndpointPreset,
    User,
    UserRole,
)
from app.schemas import (
    CourseLLMConfigResponse,
    CourseLLMConfigUpdate,
    CourseLLMConfigEndpointResponse,
    LLMEndpointPresetCreate,
    LLMEndpointPresetResponse,
    LLMEndpointPresetUpdate,
)


router = APIRouter(prefix="/api/llm-settings", tags=["LLM 配置"])

VISION_NOTICE = "LLM 连通性验证会同时校验视觉接口。只有通过视觉能力校验的端点，才能被加入课程配置并用于作业自动评分。"


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _can_manage_course_llm(user: User) -> bool:
    return user.role in [UserRole.ADMIN, UserRole.CLASS_TEACHER, UserRole.TEACHER]


def _serialize_preset(preset: LLMEndpointPreset) -> LLMEndpointPresetResponse:
    return LLMEndpointPresetResponse(
        id=preset.id,
        name=preset.name,
        base_url=preset.base_url,
        model_name=preset.model_name,
        connect_timeout_seconds=preset.connect_timeout_seconds,
        read_timeout_seconds=preset.read_timeout_seconds,
        max_retries=preset.max_retries,
        initial_backoff_seconds=preset.initial_backoff_seconds,
        is_active=preset.is_active,
        supports_vision=bool(preset.supports_vision),
        validation_status=preset.validation_status,
        validation_message=preset.validation_message,
        validated_at=preset.validated_at,
        created_at=preset.created_at,
        updated_at=preset.updated_at,
    )


def _serialize_course_config(config: CourseLLMConfig) -> CourseLLMConfigResponse:
    return CourseLLMConfigResponse(
        id=config.id,
        subject_id=config.subject_id,
        is_enabled=bool(config.is_enabled),
        response_language=config.response_language,
        daily_student_token_limit=config.daily_student_token_limit,
        daily_course_token_limit=config.daily_course_token_limit,
        estimated_chars_per_token=config.estimated_chars_per_token,
        estimated_image_tokens=config.estimated_image_tokens,
        max_input_tokens=config.max_input_tokens,
        max_output_tokens=config.max_output_tokens,
        quota_timezone=config.quota_timezone,
        system_prompt=config.system_prompt,
        teacher_prompt=config.teacher_prompt,
        endpoints=[
            CourseLLMConfigEndpointResponse(
                id=item.id,
                preset_id=item.preset_id,
                priority=item.priority,
                preset_name=item.preset.name if item.preset else None,
                model_name=item.preset.model_name if item.preset else None,
                validation_status=item.preset.validation_status if item.preset else None,
                supports_vision=item.preset.supports_vision if item.preset else None,
            )
            for item in sorted(config.endpoints or [], key=lambda row: (row.priority, row.id))
        ],
        visual_validation_notice=VISION_NOTICE,
    )


@router.get("/presets", response_model=list[LLMEndpointPresetResponse])
def list_endpoint_presets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _can_manage_course_llm(current_user):
        raise HTTPException(status_code=403, detail="You do not have access to LLM settings.")
    presets = db.query(LLMEndpointPreset).order_by(LLMEndpointPreset.id.asc()).all()
    return [_serialize_preset(item) for item in presets]


@router.post("/presets", response_model=LLMEndpointPresetResponse)
def create_endpoint_preset(
    payload: LLMEndpointPresetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can manage endpoint presets.")
    existing = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.name == payload.name.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Preset name already exists.")

    preset = LLMEndpointPreset(
        name=payload.name.strip(),
        base_url=payload.base_url.strip(),
        api_key=payload.api_key.strip(),
        model_name=payload.model_name.strip(),
        connect_timeout_seconds=payload.connect_timeout_seconds,
        read_timeout_seconds=payload.read_timeout_seconds,
        max_retries=payload.max_retries,
        initial_backoff_seconds=payload.initial_backoff_seconds,
        is_active=payload.is_active,
    )
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return _serialize_preset(preset)


@router.put("/presets/{preset_id}", response_model=LLMEndpointPresetResponse)
def update_endpoint_preset(
    preset_id: int,
    payload: LLMEndpointPresetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can manage endpoint presets.")

    preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Endpoint preset not found.")

    for field in [
        "name",
        "base_url",
        "api_key",
        "model_name",
        "connect_timeout_seconds",
        "read_timeout_seconds",
        "max_retries",
        "initial_backoff_seconds",
        "is_active",
    ]:
        value = getattr(payload, field)
        if value is not None:
            if isinstance(value, str):
                value = value.strip()
            setattr(preset, field, value)

    db.commit()
    db.refresh(preset)
    return _serialize_preset(preset)


@router.post("/presets/{preset_id}/validate", response_model=LLMEndpointPresetResponse)
def validate_preset(
    preset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _is_admin(current_user):
        raise HTTPException(status_code=403, detail="Only administrators can validate endpoint presets.")

    preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == preset_id).first()
    if not preset:
        raise HTTPException(status_code=404, detail="Endpoint preset not found.")

    ok, message = validate_endpoint_connectivity(
        base_url=preset.base_url,
        api_key=preset.api_key,
        model_name=preset.model_name,
        connect_timeout_seconds=preset.connect_timeout_seconds,
        read_timeout_seconds=preset.read_timeout_seconds,
    )
    preset.validation_status = "validated" if ok else "failed"
    preset.validation_message = message
    preset.supports_vision = bool(ok)
    preset.validated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preset)
    return _serialize_preset(preset)


@router.get("/courses/{subject_id}", response_model=CourseLLMConfigResponse)
def get_course_llm_config(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _can_manage_course_llm(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can manage course LLM config.")
    try:
        ensure_course_access(subject_id, current_user, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    config = ensure_course_llm_config(db, subject_id, current_user.id)
    db.commit()
    db.refresh(config)
    return _serialize_course_config(config)


@router.put("/courses/{subject_id}", response_model=CourseLLMConfigResponse)
def update_course_llm_config(
    subject_id: int,
    payload: CourseLLMConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not _can_manage_course_llm(current_user):
        raise HTTPException(status_code=403, detail="Only teachers can manage course LLM config.")
    try:
        ensure_course_access(subject_id, current_user, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    config = ensure_course_llm_config(db, subject_id, current_user.id)
    config.is_enabled = payload.is_enabled
    config.response_language = payload.response_language
    config.daily_student_token_limit = payload.daily_student_token_limit
    config.daily_course_token_limit = payload.daily_course_token_limit
    config.estimated_chars_per_token = payload.estimated_chars_per_token
    config.estimated_image_tokens = payload.estimated_image_tokens
    config.max_input_tokens = payload.max_input_tokens
    config.max_output_tokens = payload.max_output_tokens
    config.quota_timezone = payload.quota_timezone.strip() or "UTC"
    config.system_prompt = payload.system_prompt
    config.teacher_prompt = payload.teacher_prompt
    config.updated_by = current_user.id

    db.query(CourseLLMConfigEndpoint).filter(CourseLLMConfigEndpoint.config_id == config.id).delete()
    db.flush()
    for item in sorted(payload.endpoints, key=lambda row: (row.priority, row.preset_id)):
        preset = db.query(LLMEndpointPreset).filter(LLMEndpointPreset.id == item.preset_id).first()
        if not preset:
            raise HTTPException(status_code=400, detail=f"Endpoint preset {item.preset_id} not found.")
        if preset.validation_status != "validated" or not preset.supports_vision:
            raise HTTPException(
                status_code=400,
                detail=f"Endpoint preset {preset.name} has not passed vision validation and cannot be assigned.",
            )
        db.add(
            CourseLLMConfigEndpoint(
                config_id=config.id,
                preset_id=preset.id,
                priority=item.priority,
            )
        )

    db.commit()
    db.refresh(config)
    return _serialize_course_config(config)
