"""Shared pytest DB reset for SQLite and PostgreSQL.

PostgreSQL: SQLAlchemy ``metadata.drop_all`` can fail on FKs declared with
``use_alter=True`` (unnamed constraints). Tests use ``DROP SCHEMA public CASCADE``
on the dedicated test database instead.
"""

from __future__ import annotations

from sqlalchemy import text

from apps.backend.wailearning_backend.db.database import Base, engine


def reset_test_database_schema() -> None:
    if engine.dialect.name == "sqlite":
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            Base.metadata.drop_all(bind=conn)
            conn.execute(text("PRAGMA foreign_keys=ON"))
    else:
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
    Base.metadata.create_all(bind=engine)
