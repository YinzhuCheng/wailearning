# Async tasks and workers (LLM homework grading)

**Fact:** There is **no** Redis queue or Celery worker package in this repository for grading. Async work is modeled as **database rows** processed by an **in-process background thread** inside the API process.

**Primary implementation:** `apps/backend/courseeval_backend/llm_grading.py`.

---

## 1. Task storage

| Item | Detail |
|------|--------|
| ORM model | `HomeworkGradingTask` (`db/models.py`) |
| Creation | Router/service queues row when auto grading triggers (see homework router + helpers in `llm_grading.py`) |
| Status values | Typical lifecycle strings include `queued`, `processing`, `completed`, `failed` — confirm in model/router (grep `status=` assignments) |

Tasks are durable: restarting API leaves rows in DB; worker resumes according to stale reclaim rules.

---

## 2. Worker process model

| Component | Detail |
|-----------|--------|
| Class | `_WorkerManager` inside `llm_grading.py` |
| Start | `start_grading_worker()` → `worker_manager.start()` invoked from `main.py` lifespan when `ENABLE_LLM_GRADING_WORKER` and `LLM_GRADING_WORKER_LEADER` true |
| Thread | Daemon thread named `llm-grading-worker` |
| Stop | `worker_manager.stop()` on app shutdown |
| Concurrency | `ThreadPoolExecutor` sized by `resolve_max_parallel_grading_tasks(db)` (global policy) |

**Multi-worker gunicorn:** only the leader should drain (`LLM_GRADING_WORKER_LEADER=true`) to avoid duplicate churn; single uvicorn dev often runs leader.

---

## 3. Processing loop (simplified)

1. Poll / sleep `LLM_GRADING_WORKER_POLL_SECONDS`.
2. `claim_grading_tasks_batch(cap)` marks up to `cap` tasks as processing.
3. For each task id, `process_grading_task(task_id)` executes vendor HTTP via httpx, writes `HomeworkScoreCandidate`, updates submission summary via `refresh_submission_summary`, marks task terminal state.
4. Exceptions map to retry vs permanent failure (grep `RetryableLLMError`, `NonRetryableLLMError`).

---

## 4. Stale tasks

**Setting:** `LLM_GRADING_TASK_STALE_SECONDS` (`Settings`).

If a worker dies mid-processing, reclaim logic should allow tasks to return to queue — implementation details in `llm_grading.py` (grep `stale`).

---

## 5. Quota interaction

Before / during execution, quota policies gate token reservations (`domains/llm/` helpers). Exhaustion surfaces as task failure states + UI diagnostics — see [`../product/LLM_HOMEWORK_GUIDE.md`](../product/LLM_HOMEWORK_GUIDE.md).

---

## 6. Testing hooks

- Tests frequently patch HTTP (`httpx`) rather than calling live vendors.
- Worker may be disabled via `tests/conftest.py` defaults to reduce background interference.
- Direct helpers: `process_grading_task`, `process_next_grading_task` — used in tests.

---

## 7. Operational troubleshooting

| Symptom | Checks |
|---------|--------|
| Tasks never leave `queued` | Worker flags; DB connectivity; leader setting |
| Stuck `processing` | Stale seconds; kill orphaned workers; DB inspection |
| Unexpected score | Effective aggregate rule vs latest attempt body — see `refresh_submission_summary` |

Cross-links: [`architecture/TROUBLESHOOTING.md`](../architecture/TROUBLESHOOTING.md), [`development/TEST_EXECUTION_PITFALLS.md`](../development/TEST_EXECUTION_PITFALLS.md).

---

## 8. 待人工确认

- Exact exhaustive list of string states for `HomeworkGradingTask.status` and any legacy values still present in historical DB rows — grep model + migration-like updates.
