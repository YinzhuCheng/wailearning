# Deployment and Operations

## Scope

This document consolidates the current production, upgrade, and operational guidance for the repository. It replaces the older scattered deployment notes, upgrade runbooks, and server-specific markdown files.

## Target Production Shape

- Nginx serves the admin SPA at `/`
- Nginx serves the parent portal at `/parent/`
- Nginx proxies `/api/*` to FastAPI on `127.0.0.1:8001`
- FastAPI runs under `gunicorn` with `uvicorn` workers and `systemd`
- PostgreSQL runs locally on the same host

Typical filesystem layout:

- `/opt/dd-class/source`
- `/opt/dd-class/venv`
- `/opt/dd-class/shared/.env.production`
- `/opt/dd-class/shared/uploads`
- `/opt/dd-class/backups`
- `/var/www/wailearning.xyz/admin`
- `/var/www/wailearning.xyz/parent`

## Server Bootstrap

Use the repository scripts rather than hand-building the environment:

```bash
sudo bash ops/scripts/setup_server.sh
```

Then prepare the production env file:

```bash
sudo install -m 640 .env.production /opt/dd-class/shared/.env.production
sudo nano /opt/dd-class/shared/.env.production
```

## Required Production Settings

At minimum, set:

```dotenv
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql://ddclass:<password>@127.0.0.1:5432/ddclass
SECRET_KEY=<strong-random-value>
ALLOW_PUBLIC_REGISTRATION=false
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=<strong-admin-password>
INIT_ADMIN_REAL_NAME=System Administrator
INIT_DEFAULT_DATA=false
BACKEND_CORS_ORIGINS=https://wailearning.xyz,https://www.wailearning.xyz
TRUSTED_HOSTS=wailearning.xyz,www.wailearning.xyz,127.0.0.1,localhost
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

## Database Initialization

Use the bundled SQL script:

```bash
cp ops/scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name='ddclass' \
  -v db_user='ddclass' \
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
- backend deployment installs `ops/systemd/ddclass-backend.service` and restarts `ddclass-backend.service`
- frontend deployment builds from `apps/web/admin` and syncs `dist/` into `${ADMIN_WEB_ROOT}`
- parent deployment builds from `apps/web/parent` and syncs `dist/` into `${PARENT_WEB_ROOT}`
- both frontend deploy scripts also refresh the nginx site file from `ops/nginx/wailearning.xyz*.conf`

Recommended full deploy:

```bash
sudo bash ops/scripts/deploy_all.sh
sudo bash ops/scripts/post_deploy_check.sh
```

## Git-Based Server Updates

Preferred update path:

```bash
cd /opt/dd-class/source
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

## Validation Checklist

After deployment:

- check `systemctl status ddclass-backend`,
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
sudo -u postgres pg_dump -Fc ddclass > /opt/dd-class/backups/ddclass-$(date +%F-%H%M%S).dump
```

Shared files:

```bash
sudo tar -czf /opt/dd-class/backups/ddclass-files-$(date +%F-%H%M%S).tar.gz \
  /opt/dd-class/shared \
  /var/www/wailearning.xyz
```

If homework attachments are important in your deployment, also back up the effective upload root defined by `UPLOADS_DIR`.

## Troubleshooting

Backend logs:

```bash
sudo journalctl -u ddclass-backend -f
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
