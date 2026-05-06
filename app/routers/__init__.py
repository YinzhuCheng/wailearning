"""Router submodules for FastAPI.

`app.main` imports concrete routers directly (e.g. ``from app.routers import homework``).
This package ``__init__`` intentionally does **not** re-export every submodule: doing so
would duplicate the maintenance surface and mislead tooling into thinking all routers
must be imported here.

For tests or one-off scripts that need a single router module, prefer::

    from app.routers import llm_settings  # resolves to app/routers/llm_settings.py

"""
