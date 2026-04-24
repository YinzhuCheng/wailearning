# Behavior tests (API-level)

Tests under `tests/behavior/` exercise multi-role LLM flows via `TestClient` (same stack as other tests in `tests/`).

```bash
pytest tests/behavior -v
```

SQLite CI skips `test_r3_*` (PostgreSQL-only column guard).
