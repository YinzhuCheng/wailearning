import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.attachments import ensure_upload_directories
from app.bootstrap import (
    backfill_homework_grading_data,
    ensure_schema_updates,
    normalize_semester_catalog,
    normalize_teacher_class_assignments,
    sync_subject_semester_links,
)
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.llm_grading import start_grading_worker, worker_manager
from app.routers import (
    attendance,
    auth,
    classes,
    dashboard,
    files,
    homework,
    logs,
    materials,
    notifications,
    parent,
    points,
    scores,
    semesters,
    settings as system_settings,
    students,
    subjects,
    users,
    llm_settings,
)

if settings.APP_ENV != "production":
    Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI backend for the BIMSA-CLASS school management system.",
    version="1.0.0",
)

if settings.TRUSTED_HOSTS and "*" not in settings.TRUSTED_HOSTS:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

allow_all_origins = "*" in settings.BACKEND_CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else settings.BACKEND_CORS_ORIGINS,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(classes.router)
app.include_router(students.router)
app.include_router(scores.router)
app.include_router(attendance.router)
app.include_router(dashboard.router)
app.include_router(subjects.router)
app.include_router(users.router)
app.include_router(semesters.router)
app.include_router(logs.router)
app.include_router(points.router)
app.include_router(system_settings.router)
app.include_router(llm_settings.router)
app.include_router(files.router)
app.include_router(homework.router)
app.include_router(materials.router)
app.include_router(notifications.router)
app.include_router(parent.router)

ensure_upload_directories()


@app.on_event("startup")
def startup_tasks():
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()
    db = SessionLocal()
    try:
        normalize_teacher_class_assignments(db)
        normalize_semester_catalog(db)
        sync_subject_semester_links(db)
        backfill_homework_grading_data(db)
    finally:
        db.close()
    if settings.ENABLE_LLM_GRADING_WORKER and settings.LLM_GRADING_WORKER_LEADER:
        start_grading_worker()


@app.on_event("shutdown")
def shutdown_tasks():
    worker_manager.stop()


@app.get("/")
def root():
    return {
        "message": settings.APP_NAME,
        "status": "running",
        "environment": settings.APP_ENV,
    }


@app.get("/health")
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}


@app.get("/api/bing-background")
def get_bing_background():
    try:
        response = httpx.get(
            "https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN",
            timeout=10.0,
        )
        data = response.json()
        if data.get("images"):
            image_url = "https://www.bing.com" + data["images"][0]["url"]
            return {"url": image_url}
    except Exception as exc:
        print(f"Failed to fetch Bing background: {exc}")
    return {"url": ""}
