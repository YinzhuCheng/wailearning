# System Overview

## What the System Does

BIMSA-CLASS is a multi-role teaching-management platform for classroom administration, academic records, homework workflows, course materials, notifications, and parent access. It is designed to work as a normal school-management system even when LLM features are disabled, while also supporting course-level AI-assisted grading when configured.

## Major Capability Areas

### Identity and access

- JWT-based authentication for admin, class teacher, subject teacher, and student accounts.
- Optional student self-registration, disabled by default.
- Parent access through parent codes instead of full user accounts.
- Trusted-host and CORS controls through backend configuration.

### Class, student, and user administration

- Class creation and maintenance.
- Student roster management and batch import.
- User management for staff and students.
- Reconciliation between student accounts and roster rows during bootstrap and seed flows.
- Batch class reassignment with downstream enrollment synchronization.

### Courses and enrollments

- Subject management for required and elective courses.
- Teacher-to-course ownership.
- Required-course enrollment repair and elective self-enrollment flows.
- Roster-driven enrollment, enrollment blocking, and class-bound access checks.

### Homework and grading

- Homework publication with due dates, max score, grade precision, late rules, and max-submission limits.
- Student submission history with multiple attempts.
- Teacher review, score candidates, manual regrade, and batch regrade flows.
- Homework-grade appeals and score-composition appeals.

### Course materials and notifications

- Hierarchical material chapters and material placement.
- Class-wide, course-wide, targeted-student, and targeted-user notifications.
- Per-user read-state tracking and mark-all-read behavior.
- Notification support for grading and appeal events.

### Scores, attendance, and points

- Score entry, grade schemes, exam weights, and composition views.
- Attendance tracking and bulk attendance flows.
- Points system for rewards, ranking, and classroom incentive scenarios.

### Parent portal

- Separate frontend application under `/parent/`.
- Parent-code verification and student-bound read-only views.
- Access to scores, notifications, homework, and summary statistics.

## LLM-Centered Features

LLM support is tightly integrated with homework and course configuration.

- Endpoint presets are centrally managed by admins.
- Course-level LLM config controls whether a course uses LLM grading at all.
- Courses maintain their own quota timezone and endpoint selection order.
- Auto-grading is async and queue-backed.
- Token usage is tracked per student and per course.
- Attachments are normalized into model-friendly payloads where possible.
- Teachers can recover from failures through regrade flows without losing attempt history.

The implementation details are documented in [LLM_HOMEWORK_GUIDE.md](LLM_HOMEWORK_GUIDE.md).

## Architecture

### Backend

- FastAPI application in `app/`
- SQLAlchemy models and bootstrap migrations
- PostgreSQL as the primary database
- In-process grading worker controlled by configuration
- File handling and attachment authorization through backend routes

### Admin frontend

- Vue 3 SPA in `apps/web/admin/`
- Element Plus component layer
- Pinia state management
- Playwright E2E coverage in `tests/e2e/web-admin/` with config in `apps/web/admin/playwright.config.cjs`

### Parent portal

- Separate Vue 3 SPA in `apps/web/parent/`
- Served from `/parent/` in production

## Backend Route Groups

The application exposes these primary route groups:

- `/api/auth`
- `/api/classes`
- `/api/students`
- `/api/users`
- `/api/subjects`
- `/api/homeworks`
- `/api/llm-settings`
- `/api/materials`
- `/api/material-chapters`
- `/api/notifications`
- `/api/scores`
- `/api/attendance`
- `/api/points`
- `/api/semesters`
- `/api/settings`
- `/api/parent`
- `/api/files`
- `/api/dashboard`
- `/api/logs`

## Bootstrap Behavior

On application startup, the backend:

- creates tables if needed,
- applies schema updates,
- normalizes teacher/class and semester links,
- backfills homework grading data,
- reconciles student users and roster rows,
- optionally seeds demo data,
- optionally starts the LLM grading worker leader.

See [ADMIN_BOOTSTRAP.md](ADMIN_BOOTSTRAP.md) and [DEPLOYMENT_AND_OPERATIONS.md](DEPLOYMENT_AND_OPERATIONS.md).
