# Next Round Risk And Skip Focus

This file answers two questions:

1. What similar bugs may still exist in the repository?
2. Which skipped tests should be prioritized next round?

## 1. Likely similar bugs still worth checking

### 1.1 More "query then insert" paths may still ignore pending ORM rows

This round already confirmed two real cases:

- `course_llm_configs.subject_id`
- `course_enrollments(subject_id, student_id)`

So next round should inspect other "check then insert" paths for the same pattern, especially:

- appeal deduplication
- notification read-state writes
- `CourseLLMConfigEndpoint`
- `LLMGroup`
- homework attempt and score-candidate backfill
- latest-attempt or latest-link repair logic

### 1.2 Startup backfill and reconcile logic remains a high-risk class

This repository performs multiple startup-time repair paths:

- schema updates
- grading-data backfill
- roster/user reconcile
- student course-context preparation

Those paths are risky because they:

- run during app startup
- perform many writes in one large session
- mix database state with in-memory ORM state

Next round should continue checking whether each path is safely re-runnable.

### 1.3 Chinese text selectors remain a recurring risk

This round confirmed that one mojibake incident came from the editing chain, not from original repository history.
But the longer-term risk remains:

- tests still use many Chinese text selectors
- future command-line text editing on Windows can still reintroduce the same class of failure

Priority follow-up:

- move high-frequency selectors to `data-testid`
- reduce dependency on visible copy for locating controls

### 1.4 User list and batch-class flows should be treated as a focused risk area

Repeated full-suite failures pointed back to:

- user-row lookup
- student-row selection
- batch-class dialog flows

Possible root causes:

- default pagination
- stale or delayed list refresh
- filter residue
- visible rows not matching selected rows

This area deserves dedicated investigation instead of more assertion patching.

## 2. Skipped test names from this round

### 2.1 Confirmed skipped tests

- `tests/behavior/test_regression_llm_quota_behavior.py::test_r3_course_llm_config_columns_no_legacy_token_limits`
  - skip reason: PostgreSQL-only `information_schema` check
- `tests/test_llm_attachment_formats.py::test_rar_unencrypted_extracts_inner_txt`
  - skip reason: non-free `rar` CLI not installed
- `tests/test_llm_attachment_formats.py::test_rar_password_rejected`
  - skip reason: non-free `rar` CLI not installed

## 3. Suggested next-round priorities

### P0

- Add stable `data-testid` coverage to:
  - `Users`
  - `Subjects`
  - `Homework`
  - batch-class flows
  - personal settings
- Re-run and reduce the remaining Playwright full-suite failures
- Audit more startup and reconcile paths for session-local idempotency bugs

### P1

- Run PostgreSQL-backed checks for:
  - `test_r3_course_llm_config_columns_no_legacy_token_limits`
- Continue searching for other ORM paths that ignore pending rows

### P2

- Install the required RAR toolchain and run:
  - `test_rar_unencrypted_extracts_inner_txt`
  - `test_rar_password_rejected`
- While there, also inspect attachment handling around:
  - encrypted RAR
  - missing `unrar`
  - Windows path behavior
  - temp-directory permissions

## 4. Extra test-environment risk found this round

This is not a skip, but it should be avoided next round:

- If `pytest -rs` is launched from `C:\Windows\system32`,
  the relative `--basetemp` can resolve into the system directory.
- That can break setup for RAR-related tests with:
  - `FileNotFoundError: C:\\Windows\\system32\\.pytest_tmp\\basetemp`

Next-round rule:

- run `pytest` from repo root
- or change temp-path handling so it is anchored to the repository instead of the current shell cwd
