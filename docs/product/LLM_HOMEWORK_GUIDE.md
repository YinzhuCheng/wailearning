# LLM and Homework Guide

## Purpose

This document describes the current LLM-assisted homework implementation in the repository. It focuses on what the system actually does today: admin-managed presets, course-level routing, async grading tasks, token accounting, attachment handling, and recovery flows.

## Design Model

The LLM feature set is built around four layers:

1. Endpoint presets controlled by admins.
2. Course-level LLM configuration controlled by teachers or privileged staff.
3. Homework-level auto-grading switches and routing hints.
4. Submission and grading-task execution with queue state, retries, and billing metadata.

## Core Entities

### Presets and course config

- `LLMEndpointPreset`
  Stores base URL, API key, model name, timeout, retry, activation, and validation state.
- `CourseLLMConfig`
  Stores the course-level enable switch, prompts, and per-request `max_input_tokens` / `max_output_tokens` (used for prompt sizing and model calls). Endpoint routing (flat list or grouped failover) is stored via `CourseLLMConfigEndpoint` / `LLMGroup`.
- `LLMGlobalQuotaPolicy` (singleton row)
  Stores the **global** LLM quota calendar (`quota_timezone`), default per-student daily token cap, **token estimation knobs** used for grading pre-reservation (`estimated_chars_per_token`, `estimated_image_tokens`), and `max_parallel_grading_tasks`.
- `CourseLLMConfigEndpoint`
  Links validated presets into a course-specific endpoint order.

### Homework and grading state

- `Homework`
  Stores grading policy such as `auto_grading_enabled`, `grade_precision`, `rubric_text`, `reference_answer`, `response_language`, late rules, and `max_submissions`.
- `HomeworkSubmission`
  Summary row per homework and student.
- `HomeworkAttempt`
  Immutable submission history rows.
- `HomeworkScoreCandidate`
  Candidate scores from auto-grading or teacher review.
- `HomeworkGradingTask`
  Async grading queue rows with retry, endpoint, and token metadata.

### Token accounting

- `LLMTokenUsageLog`
  Records successful usage per student and per course.
- Student overrides and global quota policy control the effective budget.

## Admin Workflow

Admins can:

- create and update endpoint presets,
- activate or deactivate presets,
- validate text and vision capability,
- tune timeout and retry behavior,
- define global quota defaults **and** the global quota calendar timezone,
- configure token estimation knobs used for grading reservations,
- set per-student quota overrides.

The system assumes presets are the reusable source of truth. Courses do not create raw endpoints independently.

## Course Workflow

Teachers configure LLM behavior per course.

- Enable or disable LLM use at the course level.
- Set prompts and response language.
- Choose endpoint order (or grouped routing) from validated presets.
- Tune per-request input/output token limits for grading prompts.

Quota day boundaries and student daily caps are **not** configured per course anymore; see `LLMGlobalQuotaPolicy` and admin LLM settings.

## Homework Workflow

When homework auto-grading is enabled:

- a student submission creates or updates a submission summary,
- the submission creates a new attempt row,
- the backend enqueues a grading task,
- the grading worker claims queued tasks,
- the worker resolves routing and quota checks,
- the worker calls the selected endpoint,
- the system stores score candidates and updates the submission summary.

Teachers can still:

- manually review,
- regrade,
- batch regrade,
- inspect failures and logs,
- resolve student appeals.

## Attachment Handling

The implementation supports attachment-aware grading inputs.

- Images can be routed to vision-capable presets.
- PDFs, notebooks, archives, and extracted text can be transformed into model payloads.
- Attachments are accessed through authenticated backend routes rather than public static file exposure.
- The exact payload shape depends on file type, endpoint capability, and extraction outcome.

This is a high-risk integration area and should be tested with real failure cases, not only happy paths.

## Async Worker Behavior

The grading worker is database-backed and configuration-driven.

- `ENABLE_LLM_GRADING_WORKER` toggles the worker.
- `LLM_GRADING_WORKER_LEADER` decides whether this process is the active leader.
- `LLM_GRADING_TASK_STALE_SECONDS` controls stale-task reclamation.
- The worker can recover tasks stuck in processing state.
- Endpoint failover and retry behavior are part of task processing, not just UI concerns.

In single-process local development, one process can both serve the API and drain the queue. In multi-instance production, only one intended leader should normally run task draining.

## Quotas and Timezones

Practical rules (current implementation):

- The **numeric** per-student daily cap comes from `LLMGlobalQuotaPolicy.default_daily_student_tokens`, optionally overridden per student (`LLMStudentTokenOverride`).
- The **calendar day** for reservations + `LLMTokenUsageLog` / discussion logs is determined by **`LLMGlobalQuotaPolicy.quota_timezone`** (same clock for all courses).
- **Precheck / reservation** for grading uses the global policy’s estimation parameters (`estimated_chars_per_token`, `estimated_image_tokens`) when sizing expected prompt usage.
- Usage rows still record `subject_id` for attribution/analytics, but **enforcement** is against the **student’s total** usage for that global calendar day (not a separate per-course cap pool).

Historical note: older docs described per-course `quota_timezone` for student quotas; that behavior was removed in favor of the global policy row above.

## Failure and Recovery Patterns

The implementation supports these recovery paths:

- disabled course config causes task failure without corrupting prior attempts,
- quota exhaustion blocks or fails the affected task while allowing later recovery,
- endpoint failure can fall through to another configured preset,
- retryable transport failures can succeed later,
- teacher regrade can replace a failed auto-grading outcome with a successful one,
- relogin or refresh should recover the authoritative grading state from the backend.

## Observability

Useful operational signals include:

- grading task status,
- error code and error message,
- endpoint index and attempt count,
- billed token fields,
- notification events for grading completion and appeal handling,
- student-visible quota summaries.

## Recommended Documentation-Level Rules

- Treat the backend state as authoritative over UI animations or stale local cache.
- Prefer describing route behavior, entity ownership, and recovery semantics over fragile UI copy.
- Whenever LLM behavior changes, update this document and the regression tests together.

## Related Docs

- [System Overview](../architecture/SYSTEM_OVERVIEW.md)
- [Development and Testing](../development/DEVELOPMENT_AND_TESTING.md)
- [Deployment and Operations](../operations/DEPLOYMENT_AND_OPERATIONS.md)
