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
            # SQLAlchemy creates PostgreSQL ENUM types as standalone pg types; they can survive
            # odd dependency ordering relative to tables. Drop any enum types left in public
            # so metadata.create_all can recreate them cleanly.
            conn.execute(
                text(
                    """
                    DO $$
                    DECLARE r RECORD;
                    BEGIN
                      FOR r IN (
                        SELECT t.typname AS name
                        FROM pg_type t
                        JOIN pg_namespace n ON n.oid = t.typnamespace
                        WHERE n.nspname = 'public' AND t.typtype = 'e'
                      )
                      LOOP
                        EXECUTE format('DROP TYPE IF EXISTS public.%I CASCADE', r.name);
                      END LOOP;
                    END $$;
                    """
                )
            )
    Base.metadata.create_all(bind=engine)
