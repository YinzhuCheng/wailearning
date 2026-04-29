# DD-CLASS Production Deployment Guide

This guide targets Alibaba Cloud ECS on Ubuntu 22.04, Debian 12, and Alibaba Cloud Linux or CentOS-like systems.

**First-time / empty server (order of steps + why DB must come before `deploy_all`):** see `docs/FRESH_SERVER_DEPLOY_CN.md` (Chinese).

If you want the operational checklist for first go-live, DNS cutover, acceptance, and rollback, also read `RUNBOOK_ALIYUN.md`.
If you want a data-safety-focused upgrade guide and a safer deployment example script, also read `ALIYUN_SAFE_UPGRADE.md` and `scripts/example_safe_upgrade_aliyun.sh`.

**Git on the server (branch checkout vs. “real” deploy failures):** when you deploy from a clone on ECS, failures often come from assuming `origin/<branch>` exists after a plain `git fetch`, from dirty working trees blocking `checkout`, or from SSH heredocs that never closed. Read **`docs/DEPLOY_GIT_ROBUSTNESS.md`** (mechanics) and **`docs/DEPLOYMENT_POSTMORTEM_CN.md`** (field lessons). **`scripts/redeploy.sh`** and **`scripts/pull_and_deploy.sh`** use an explicit refspec fetch via **`scripts/lib/git_sync_server.sh`**. Optional **`GIT_RESET_WORKTREE_BEFORE_FETCH=1`** backs up `git diff` then hard-resets before fetching (see the robustness doc).

**When is a deploy “done”?** A clean `git status` and a passing public health URL are not sufficient by themselves. Treat a release as verified only after **`deploy_all.sh`** has finished, **`scripts/post_deploy_check.sh`** has passed (local + public health, `nginx -t`, systemd), and **`git log -1`** matches the intended revision—the check script prints the repo `HEAD` to make that obvious.

### Why the admin UI can look “not updated” while the API works

The browser loads static files from **`/var/www/.../admin`**, rebuilt only when **`deploy_frontend.sh`** runs successfully inside **`deploy_all.sh`** (or when you use **`FRONTEND_ONLY=1`** with **`redeploy.sh`**). Typical failure modes:

- **`deploy_all.sh` did not finish** (error during backend or parent portal step), so **`deploy_frontend.sh` never ran**.
- **Wrong Git tree**: **`SKIP_GIT=1`** or SSH into the wrong directory, so **`npm run build`** repackages **old** `frontend/` sources.
- **Wrong branch**: **`redeploy.sh`** defaults **`GIT_BRANCH=main`**; always set **`GIT_BRANCH=<your branch>`** when releasing from a feature branch.
- **Wrong `REPO_DIR`**: **`pull_and_deploy.sh`** used to default to **`/root/dd-class`**; production is usually **`/opt/dd-class/source`**. Unset **`REPO_DIR`** now prefers **`/opt/dd-class/source`** when it is a git clone (see **`scripts/lib/deploy_repo_dir.sh`**). Override with **`REPO_DIR=...`** if your clone lives elsewhere.
- **Browser cache**: hard refresh or try an incognito window after a verified deploy.

**`redeploy.sh`** and **`pull_and_deploy.sh`** print the short **`HEAD`** before **`deploy_all`** so logs show which commit was built.

### Upgrade gotchas (already-deployed servers)

- **`checkout` blocked by local edits**: If you see *local changes would be overwritten by checkout*, either set **`GIT_RESET_WORKTREE_BEFORE_FETCH=1`** (hard reset + clean before fetch) or rely on the default **`GIT_AUTO_STASH_ON_CHECKOUT_CONFLICT=1`**, which saves a patch under **`BACKUP_DIR`** and runs **`git stash -u`** once before retrying checkout. Set **`GIT_AUTO_STASH_ON_CHECKOUT_CONFLICT=0`** to fail fast instead.
- **`sudo -u postgres pg_dump` from `/root`**: PostgreSQL may log *could not change directory to "/root"*; it is usually harmless. Run dumps from a neutral cwd (the scripts use **`(cd /tmp && sudo -u postgres pg_dump ...)`** when **`SAFE_BACKUP_BEFORE_DEPLOY=1`**).
- **Optional pre-upgrade backup**: Set **`SAFE_BACKUP_BEFORE_DEPLOY=1`** on **`redeploy.sh`** / **`pull_and_deploy.sh`** to archive **`DB_NAME`** (default `ddclass`) and **`SHARED_DIR`** (default `/opt/dd-class/shared`) into **`BACKUP_DIR`** before Git sync.

## Architecture

- Nginx serves the admin SPA at `/`
- Nginx serves the parent portal SPA at `/parent/`
- Nginx proxies `/api/*` to FastAPI on `127.0.0.1:8001`
- FastAPI runs under `gunicorn + uvicorn worker` with `systemd`
- PostgreSQL runs locally on the same server

## Directory Layout

- `/opt/dd-class/source` - deployed repository copy
- `/opt/dd-class/venv` - Python virtual environment
- `/opt/dd-class/shared/.env.production` - backend production env file
- `/opt/dd-class/backups` - backup directory
- `/var/www/wailearning.xyz/admin` - built admin frontend
- `/var/www/wailearning.xyz/parent` - built parent portal

## 1. Prepare the Server

Run:

```bash
sudo bash scripts/setup_server.sh
```

The setup script auto-detects `apt-get`, `dnf`, or `yum`, and configures either `ufw` or `firewalld` when available.

## 2. Create the Backend Env File

Create `/opt/dd-class/shared/.env.production` from the repository template:

```bash
sudo install -m 640 .env.production /opt/dd-class/shared/.env.production
sudo nano /opt/dd-class/shared/.env.production
```

Replace every `CHANGE_ME` value before continuing.

Generate a strong secret key:

```bash
openssl rand -hex 32
```

Recommended homework/LLM-related settings for the current architecture:

```dotenv
ALLOW_PUBLIC_REGISTRATION=false
ENABLE_LLM_GRADING_WORKER=true
LLM_GRADING_WORKER_LEADER=true
LLM_GRADING_WORKER_POLL_SECONDS=2
LLM_GRADING_TASK_STALE_SECONDS=600
INIT_DEFAULT_DATA=true
```

When **`INIT_DEFAULT_DATA=true`** (the application default), first startup also **idempotently** seeds a demo teaching bundle: accounts **`teacher`** and **`stu1`–`stu5`** (initial password **`111111`** shared), demo class **人工智能1班**, required course **数据挖掘**, elective **大语言模型** (sample material + homework), and the first required-course homework with full rubric text—see `app/demo_course_seed.py`. Set **`INIT_DEFAULT_DATA=false`** in production if you do not want these accounts.

Notes:

- `ALLOW_PUBLIC_REGISTRATION=false` is the recommended production default.
- Only one backend instance should normally set `LLM_GRADING_WORKER_LEADER=true`; other API instances should keep it `false`.
- The grading worker is database-backed and runs inside the FastAPI process, so leader election is configuration-based rather than automatic.

## 3. Initialize PostgreSQL

Run the SQL script with psql variables.

If your repository is under `/root/...`, avoid passing a file path inside `/root` to the `postgres` user directly.
Using `/tmp/init_db.sql` works reliably across environments:

```bash
cp scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name='ddclass' \
  -v db_user='ddclass' \
  -v db_password='REPLACE_WITH_A_STRONG_DB_PASSWORD' \
  -f /tmp/init_db.sql
```

Make sure the values match `DATABASE_URL` in `/opt/dd-class/shared/.env.production`.

## 4. Deploy the Backend

```bash
sudo bash scripts/deploy_backend.sh
```

Check the service:

```bash
sudo systemctl status ddclass-backend --no-pager
sudo journalctl -u ddclass-backend -n 100 --no-pager
```

If homework auto-grading is enabled in production, also confirm the leader instance is running with:

```bash
sudo systemctl show ddclass-backend --property=Environment --no-pager
```

And make sure the effective environment includes `LLM_GRADING_WORKER_LEADER=true` only on the intended worker leader.

## 5. Deploy the Admin Frontend

```bash
sudo bash scripts/deploy_frontend.sh
```

## 6. Deploy the Parent Portal

The parent portal is a separate Vite application and should be deployed independently. It is served from `/parent/`.

```bash
sudo bash scripts/deploy_parent_portal.sh
```

## 7. Configure DNS

Create these DNS records:

- `A wailearning.xyz -> <your ECS public IP>`
- `A www.wailearning.xyz -> <your ECS public IP>`

Wait until both records resolve correctly.

## 8. Enable HTTPS

After DNS is ready and Nginx is already serving HTTP:

```bash
sudo certbot --nginx -d wailearning.xyz -d www.wailearning.xyz
```

Enable automatic renewal check:

```bash
sudo systemctl status certbot.timer --no-pager
```

## 9. Validation Checklist

- Open `http://wailearning.xyz` and confirm the admin login page loads
- Open `http://wailearning.xyz/parent/` and confirm the parent portal loads
- Open `http://wailearning.xyz/health` and confirm the backend health endpoint returns `healthy`
- Log in with the bootstrap admin account configured in `.env.production`
- Confirm there are no failing Nginx requests or backend tracebacks
- In the admin UI, create or validate at least one LLM endpoint preset if you plan to use homework auto-grading
- In the course UI, confirm course-level LLM configuration can be opened and saved

## 10. Logs and Troubleshooting

Backend:

```bash
sudo journalctl -u ddclass-backend -f
```

Nginx:

```bash
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

PostgreSQL:

```bash
sudo journalctl -u postgresql -n 100 --no-pager
```

## 11. Update Workflow

Prefer the full git-align + deploy path (sets remote-tracking refs explicitly and can optionally discard local edits—see **`docs/DEPLOY_GIT_ROBUSTNESS.md`**):

```bash
cd /opt/dd-class/source
sudo GIT_BRANCH=main GIT_REMOTE=origin bash scripts/redeploy.sh
```

If the tree on the server must be wiped before pull (uncommitted edits blocking checkout), use:

```bash
sudo GIT_RESET_WORKTREE_BEFORE_FETCH=1 GIT_BRANCH=main bash scripts/redeploy.sh
```

For a conservative upgrade (database + shared tarball before Git sync), use:

```bash
cd /opt/dd-class/source
sudo SAFE_BACKUP_BEFORE_DEPLOY=1 GIT_BRANCH=main GIT_REMOTE=origin bash scripts/redeploy.sh
```

If you prefer not to auto-stash when checkout conflicts (fail fast instead):

```bash
sudo GIT_AUTO_STASH_ON_CHECKOUT_CONFLICT=0 GIT_BRANCH=main bash scripts/redeploy.sh
```

After updating the code on the server without `redeploy.sh`, still run checks:

```bash
sudo bash scripts/deploy_all.sh
sudo bash scripts/post_deploy_check.sh
```

If the backend is slow to become ready on your server size, you can increase health check retry behavior:

```bash
LOCAL_HEALTH_RETRIES=60 LOCAL_HEALTH_INTERVAL_SECONDS=1 \
  sudo bash scripts/post_deploy_check.sh
```

## 12. Backups

Database backup:

```bash
sudo -u postgres pg_dump -Fc ddclass > /opt/dd-class/backups/ddclass-$(date +%F-%H%M%S).dump
```

Static file and env backup:

```bash
sudo tar -czf /opt/dd-class/backups/ddclass-files-$(date +%F-%H%M%S).tar.gz \
  /opt/dd-class/shared \
  /var/www/wailearning.xyz
```

If you use homework attachments heavily, also back up the upload root defined by `UPLOADS_DIR` (or the default app `uploads/attachments` directory) so historical homework attempts remain reproducible.
