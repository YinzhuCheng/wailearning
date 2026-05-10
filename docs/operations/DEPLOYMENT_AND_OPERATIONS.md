# Deployment and Operations

## Scope

This document consolidates the current production, upgrade, and operational guidance for the repository. It replaces the older scattered deployment notes, upgrade runbooks, and server-specific markdown files.

Environment variables referenced below are documented field-by-field in [../architecture/CONFIGURATION_REFERENCE.md](../architecture/CONFIGURATION_REFERENCE.md) (derived from `apps/backend/courseeval_backend/core/config.py`). Keep deploy templates aligned with that file when defaults change.

## Target Production Shape

- Nginx serves the admin SPA at `/`
- Nginx serves the parent portal at `/parent/`
- Nginx proxies `/api/*` to FastAPI on `127.0.0.1:8001`
- FastAPI runs under `gunicorn` with `uvicorn` workers and `systemd`
- PostgreSQL runs locally on the same host

Typical filesystem layout:

- `/opt/courseeval/source`
- `/opt/courseeval/venv`
- `/opt/courseeval/shared/.env.production`
- `/opt/courseeval/shared/uploads`
- `/opt/courseeval/backups`
- `/var/www/courseeval.example/admin`
- `/var/www/courseeval.example/parent`

**Repository source tree note (not production-critical):** the Git checkout is a multi-app monorepo (`apps/`, `docs/`, `ops/`, `tests/`). Test hygiene utilities such as the redundancy auditor live under `tests/devtools/` in source control. Production servers do not need those files unless you intentionally run repository QA on the host — deployment automation remains under `ops/scripts/`. Structural truth vs local artifacts: [../architecture/REPOSITORY_STRUCTURE.md](../architecture/REPOSITORY_STRUCTURE.md).

## Server Bootstrap

Use the repository scripts rather than hand-building the environment:

```bash
sudo bash ops/scripts/setup_server.sh
```

Then prepare the production env file:

```bash
sudo install -m 640 .env.production /opt/courseeval/shared/.env.production
sudo nano /opt/courseeval/shared/.env.production
```

## Required Production Settings

At minimum, set:

```dotenv
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql://courseeval:<password>@127.0.0.1:5432/courseeval
SECRET_KEY=<strong-random-value>
ALLOW_PUBLIC_REGISTRATION=false
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=<strong-admin-password>
INIT_ADMIN_REAL_NAME=System Administrator
INIT_DEFAULT_DATA=false
BACKEND_CORS_ORIGINS=https://courseeval.example,https://www.courseeval.example
TRUSTED_HOSTS=courseeval.example,www.courseeval.example,127.0.0.1,localhost
ENABLE_LLM_GRADING_WORKER=true
LLM_GRADING_WORKER_LEADER=true
LLM_GRADING_WORKER_POLL_SECONDS=2
LLM_GRADING_TASK_STALE_SECONDS=600
REQUIRE_STRONG_SECRETS=true
```

Production rules:

- never keep placeholder database credentials,
- never keep the default weak secret,
- normally keep `ALLOW_PUBLIC_REGISTRATION=false`,
- use `INIT_DEFAULT_DATA=false` unless you intentionally want demo accounts and demo courses,
- set `TRUSTED_HOSTS` and `BACKEND_CORS_ORIGINS` deliberately instead of relying on development defaults,
- consider `REQUIRE_STRONG_SECRETS=true` even outside strict production startup paths so weak secrets fail early,
- only one production backend leader should usually run the grading worker.
- Optional: set `FRONTEND_ADMIN_BASE_URL` to the public admin origin (for example `https://courseeval.example`) so **忘记密码** notifications include an absolute link to the password-reset screen; if unset, the notification still contains a relative `/users?...` path that works when opened inside the same admin site.

## Administrator password after deployment (SSH)

If you can SSH into the application server, you can reset any user password (including the bootstrap `INIT_ADMIN_USERNAME`) **without using the web UI** by running the bundled script against the production virtualenv and `.env.production`:

```bash
cd /opt/courseeval/source
sudo bash ops/scripts/reset_user_password.sh admin 'YourNewStrongPasswordHere!'
```

The script updates the password hash in the database and increments `token_version` so existing JWT sessions for that user are invalidated. Alternatively, set `INIT_ADMIN_PASSWORD` before the **first** bootstrap run when `INIT_DEFAULT_DATA=true`; for an already-deployed database, prefer the script above or an in-app admin reset from **用户管理**.

## Database Initialization

Use the bundled SQL script:

```bash
cp ops/scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name='courseeval' \
  -v db_user='courseeval' \
  -v db_password='REPLACE_WITH_A_STRONG_DB_PASSWORD' \
  -f /tmp/init_db.sql
```

## Deployment Scripts

Primary scripts:

- `ops/scripts/deploy_all.sh`
- `ops/scripts/deploy_backend.sh`
- `ops/scripts/deploy_frontend.sh`
- `ops/scripts/deploy_parent_portal.sh`
- `ops/scripts/post_deploy_check.sh`
- `ops/scripts/redeploy.sh`
- `ops/scripts/pull_and_deploy.sh`

Implementation notes that matter operationally:

- `deploy_backend.sh` creates `${APP_ROOT}/shared/uploads` and migrates legacy `uploads/` content there when present
- backend deployment installs `ops/systemd/courseeval-backend.service` and restarts `courseeval-backend.service`
- frontend deployment builds from `apps/web/admin` and syncs `dist/` into `${ADMIN_WEB_ROOT}`
- parent deployment builds from `apps/web/parent` and syncs `dist/` into `${PARENT_WEB_ROOT}`
- both frontend deploy scripts also refresh the nginx site file from `ops/nginx/courseeval.example*.conf`

Recommended full deploy:

```bash
sudo bash ops/scripts/deploy_all.sh
sudo bash ops/scripts/post_deploy_check.sh
```

## Git-Based Server Updates

Preferred update path:

```bash
cd /opt/courseeval/source
sudo GIT_BRANCH=main GIT_REMOTE=origin bash ops/scripts/redeploy.sh
```

Useful variants:

- `GIT_RESET_WORKTREE_BEFORE_FETCH=1` when local server edits are blocking checkout.
- `SAFE_BACKUP_BEFORE_DEPLOY=1` when you want a pre-upgrade database and shared-data backup.
- `GIT_AUTO_STASH_ON_CHECKOUT_CONFLICT=0` when you want fail-fast behavior instead of auto-stash.
- `FRONTEND_ONLY=1` when you intentionally want only the admin SPA rebuilt and deployed.
- `APP_URL=https://...` when you want the post-deploy public check to hit a specific public hostname.

## Safe Upgrade Principles

When upgrading a live system:

1. Back up the database first.
2. Back up shared uploads and env files.
3. Align the intended git revision explicitly.
4. Deploy backend and frontends together unless you have a deliberate split rollout.
5. Validate with health checks, logs, and the intended git `HEAD`.

Do not treat a clean `git status` or a single public URL response as proof that deployment finished.

### CourseEval normalization prechecks

Before deploying the CourseEval normalization line to a database that predates the package/branding cleanup, confirm these invariants or run a dry deployment against a restored backup:

- `users.student_id` is populated for active student login accounts that should participate in quota, homework, discussion, and course enrollment flows. The runtime reconciliation path may repair default/demo drift, but feature code should not rely on `username == student_no` as a relationship.
- Required courses have `subject_class_links` rows for each administrative class that should auto-enroll. Student and class-teacher course access no longer falls back to `subjects.class_id`; that column remains a primary/display anchor for compatibility-heavy rows.
- Upload files are present under the effective `UPLOADS_DIR` / `${APP_ROOT}/shared/uploads` path. The deployment script can migrate a legacy `uploads/` directory when it is still colocated with the deployment root, but operators should verify attachment URLs before cutting over.
- System settings in the database already contain the intended CourseEval branding. Frontend normalization no longer rewrites stored legacy brand text at render time.
- Service and Nginx names match the current templates: `courseeval-backend.service` and `ops/nginx/courseeval.example*.conf`.

## Validation Checklist

After deployment:

- check `systemctl status courseeval-backend`,
- run `curl http://127.0.0.1:8001/health`,
- run `sudo nginx -t`,
- verify the admin frontend loads,
- verify the parent portal loads,
- verify backend logs are clean,
- confirm the repo `HEAD` matches the intended revision,
- if using LLM grading, confirm endpoint presets and course-level config still load.

## LLM-Specific Production Concerns

- Presets must be valid before teachers can rely on them.
- Worker leadership must be explicit in multi-instance deployments.
- Token quotas and endpoint retries are production behavior, not just test behavior.
- If attachments matter operationally, include the uploads directory in your backup plan.

## Backups

Database:

```bash
sudo -u postgres pg_dump -Fc courseeval > /opt/courseeval/backups/courseeval-$(date +%F-%H%M%S).dump
```

Shared files:

```bash
sudo tar -czf /opt/courseeval/backups/courseeval-files-$(date +%F-%H%M%S).tar.gz \
  /opt/courseeval/shared \
  /var/www/courseeval.example
```

If homework attachments are important in your deployment, also back up the effective upload root defined by `UPLOADS_DIR`.

## Troubleshooting

Backend logs:

```bash
sudo journalctl -u courseeval-backend -f
```

Nginx logs:

```bash
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

PostgreSQL:

```bash
sudo journalctl -u postgresql -n 100 --no-pager
```

## Related Docs

- [LLM and Homework Guide](../product/LLM_HOMEWORK_GUIDE.md)
- [Admin Bootstrap and Demo Seed](ADMIN_BOOTSTRAP.md)
- [Git Workflow](../development/GIT_WORKFLOW.md)
