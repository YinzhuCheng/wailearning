from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from apps.backend.courseeval_backend.core.config import settings

engine_kwargs = {"pool_pre_ping": True}

if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


if settings.DATABASE_URL.startswith("sqlite"):
    def _set_sqlite_foreign_keys(dbapi_connection, connection_record):  # pragma: no cover - connection hook
        try:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass

    event.listen(engine, "connect", _set_sqlite_foreign_keys)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
