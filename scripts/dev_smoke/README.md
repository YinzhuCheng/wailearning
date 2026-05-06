# Dev smoke scripts (non-pytest)

These Python files are **manual** HTTP or direct-DB checks against a **running** backend (typically `http://127.0.0.1:8001`). They were moved from the repository root because their former names (`test_*.py`) collided with pytest discovery when contributors ran `pytest` without arguments.

## When to use

- Quick sanity checks against a live stack after deployment or local `uvicorn`.
- They are **not** part of CI automated tests. CI and agents should run:

```bash
cd <REPO_ROOT>
pytest tests/ -q
```

## Pitfalls (for LLM / human maintainers)

| Symptom | Likely cause |
|--------|----------------|
| `ConnectionError` / refused | Backend not listening on `BASE_URL` in the script. |
| `401` / empty lists | Default admin password in `.env` differs from script (`admin123` vs `ChangeMe123!` in `app/config.py`). Align credentials or export env-specific URLs. |
| Script “does nothing” in pytest | These files are intentionally **outside** `tests/`; `pytest.ini` sets `testpaths = tests` so root collection no longer picks them up. |

## Files

- `manual_smoke_classes_users.py` — classes + users list.
- `manual_smoke_semesters_dashboard.py` — semesters + dashboard stats.
- `manual_smoke_create_class_teacher.py` — POST user (class_teacher).
- `manual_smoke_users_crud.py` — broader users API walkthrough.
- `manual_smoke_points.py` — points stats/rules/items.
- `manual_smoke_logs.py` — logs list + stats.
- `manual_smoke_settings.py` — public + admin settings.
- `manual_smoke_login_dashboard.py` — login + semesters + dashboard (has `if __name__ == "__main__"`).
- `manual_dashboard_direct_db.py` — imports SQLAlchemy session and calls router functions directly (requires DB + seeded admin; uses repo-relative `sys.path`).
