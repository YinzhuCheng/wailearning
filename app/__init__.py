from __future__ import annotations

from pathlib import Path


_PACKAGE_ROOT = Path(__file__).resolve().parent
_BACKEND_APP = _PACKAGE_ROOT.parent / "apps" / "backend" / "app"

# Compatibility shim: the real backend package lives under apps/backend/app,
# but a large part of the codebase and deployment surface still imports app.*.
__path__ = [str(_BACKEND_APP)]
