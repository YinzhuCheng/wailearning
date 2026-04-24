# DD-CLASS Production Deployment Guide

This guide targets Alibaba Cloud ECS on Ubuntu 22.04, Debian 12, and Alibaba Cloud Linux or CentOS-like systems.

**First-time / empty server (order of steps + why DB must come before `deploy_all`):** see `docs/FRESH_SERVER_DEPLOY_CN.md` (Chinese).

**Pitfalls and a copy-paste flow for public-IP + HTTP(80) only (no domain / no cert yet):** see `docs/DEPLOY_PITFALLS_IP_HTTP_CN.md` (Chinese).

If you want the operational checklist for first go-live, DNS cutover, acceptance, and rollback, also read `RUNBOOK_ALIYUN.md`.
If you want a data-safety-focused upgrade guide and a safer deployment example script, also read `ALIYUN_SAFE_UPGRADE.md` and `scripts/example_safe_upgrade_aliyun.sh`.

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
```

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

After updating the code on the server:

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
