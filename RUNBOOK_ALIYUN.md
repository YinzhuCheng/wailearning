# DD-CLASS Alibaba Cloud Runbook

This runbook is for the first production go-live of `wailearning.xyz` on Alibaba Cloud ECS.

If you want the concise deployment guide, read `DEPLOY.md`.
If you want the execution order, expected results, acceptance checks, and rollback steps, use this file.
If you want a deployment/upgrade guide that focuses specifically on **protecting original homework, materials, scores, and user data during code updates**, also read `ALIYUN_SAFE_UPGRADE.md`.

## 0. Target Topology

- ECS OS: Ubuntu 22.04, Debian 12, Alibaba Cloud Linux, or CentOS-like systems
- Reverse proxy: Nginx
- Backend: FastAPI on `127.0.0.1:8001`
- Frontend admin: static files served at `/`
- Parent portal: static files served at `/parent/`
- Database: PostgreSQL on the same host
- Domain: `wailearning.xyz`
- HTTPS: Let's Encrypt via Certbot

## 1. Local Preparation

Before touching the server, prepare these items locally:

- A reachable Alibaba Cloud ECS public IP
- A domain you control in Alibaba Cloud DNS or another DNS provider
- SSH login to the ECS instance
- Strong passwords for PostgreSQL and the bootstrap admin
- A random 64-hex-character secret key

Generate a backend secret key locally:

```bash
openssl rand -hex 32
```

Confirm the repo contains these deployment assets:

- `DEPLOY.md`
- `RUNBOOK_ALIYUN.md`
- `scripts/setup_server.sh`
- `scripts/init_db.sql`
- `scripts/deploy_all.sh`
- `scripts/post_deploy_check.sh`
- `systemd/ddclass-backend.service`
- `nginx/wailearning.xyz.conf`

## 2. Upload Code to ECS

Option A, upload the local directory:

```bash
scp -r ./dd-class root@<ECS_PUBLIC_IP>:/root/
```

Option B, clone on the server:

```bash
ssh root@<ECS_PUBLIC_IP>
cd /root
git clone https://gitee.com/joyapple2020/dd-class.git
cd dd-class
```

If you are using your own fork, replace the repository URL accordingly.

## 3. Initialize the Server

Login to ECS:

```bash
ssh root@<ECS_PUBLIC_IP>
cd /root/dd-class
chmod +x scripts/*.sh
```

Run the base setup:

```bash
sudo bash scripts/setup_server.sh
```

Expected result:

- Nginx installed and enabled
- PostgreSQL installed and enabled
- Python, venv, Node.js, rsync, Certbot installed
- `/opt/dd-class` created
- `/var/www/wailearning.xyz/admin` created
- `/var/www/wailearning.xyz/parent` created
- `ddclass` system user created
- On Ubuntu or Debian, `ufw` rules are applied when available
- On Alibaba Cloud Linux or CentOS-like systems, `firewalld` rules are applied when available

Quick checks:

```bash
node -v
python3 -V
sudo systemctl status nginx --no-pager
sudo systemctl status postgresql --no-pager
```

## 4. Configure the Production Env File

Install the template:

```bash
sudo install -m 640 .env.production /opt/dd-class/shared/.env.production
sudo nano /opt/dd-class/shared/.env.production
```

Set at least these values:

```dotenv
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql://ddclass:<DB_PASSWORD>@127.0.0.1:5432/ddclass
SECRET_KEY=<YOUR_RANDOM_SECRET>
BACKEND_CORS_ORIGINS=https://wailearning.xyz,https://www.wailearning.xyz
TRUSTED_HOSTS=wailearning.xyz,www.wailearning.xyz,127.0.0.1,localhost
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=<YOUR_STRONG_ADMIN_PASSWORD>
INIT_ADMIN_REAL_NAME=System Administrator
INIT_DEFAULT_DATA=true
ALLOW_PUBLIC_REGISTRATION=false
ENABLE_LLM_GRADING_WORKER=true
LLM_GRADING_WORKER_LEADER=true
LLM_GRADING_WORKER_POLL_SECONDS=2
LLM_GRADING_TASK_STALE_SECONDS=600
```

Do not keep any `CHANGE_ME` values.

Additional notes for the current homework grading architecture:

- `ALLOW_PUBLIC_REGISTRATION` should stay `false` in production unless you intentionally expose a student self-registration flow.
- `LLM_GRADING_WORKER_LEADER=true` should only be enabled on one backend instance at a time. If you deploy multiple FastAPI processes or multiple ECS nodes, select a single worker leader.
- The grading worker is currently a database-backed in-process worker. It can safely reclaim stale tasks, but it is still not a replacement for a dedicated external queue.

## 5. Initialize PostgreSQL

Create the database and database user. The password **must** match `DATABASE_URL` in `/opt/dd-class/shared/.env.production`.

If the repository lives under `/root/...`, run `psql` from a world-readable working directory and pass a path `postgres` can read (avoids the harmless "could not change directory" message):

```bash
cd /tmp
cp /root/dd-class/scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name='ddclass' \
  -v db_user='ddclass' \
  -v db_password='REPLACE_WITH_A_STRONG_DB_PASSWORD' \
  -f /tmp/init_db.sql
```

Adjust `/root/dd-class` to your clone path. See also `DEPLOY.md` and `docs/FRESH_SERVER_DEPLOY_CN.md`.

Validate:

```bash
sudo -u postgres psql -lqt | grep ddclass
sudo -u postgres psql -d ddclass -c '\conninfo'
```

Expected result:

- Database `ddclass` exists
- Role `ddclass` exists
- The role can connect to the database

## 6. First Deployment

Run the full deployment:

```bash
sudo bash scripts/deploy_all.sh
```

This will:

- Sync the repository into `/opt/dd-class/source`
- Create or update the Python virtualenv
- Install backend dependencies
- Bootstrap database tables and default data
- Apply schema patching and homework grading data backfill on startup
- Install the `systemd` service
- Build the admin frontend
- Build the parent portal frontend
- Install and reload Nginx config

## 7. Pre-DNS Validation

Check local service status on the server before touching DNS:

```bash
sudo systemctl status ddclass-backend --no-pager
curl -fsS http://127.0.0.1:8001/health
curl -I http://127.0.0.1
sudo nginx -t
```

Expected result:

- `ddclass-backend` is `active (running)`
- `/health` returns JSON with `status`
- Nginx config test is successful

If the backend fails to start:

```bash
sudo journalctl -u ddclass-backend -n 100 --no-pager
```

## 8. Configure DNS

In Alibaba Cloud DNS, add:

- `A` record: `wailearning.xyz -> <ECS_PUBLIC_IP>`
- `A` record: `www.wailearning.xyz -> <ECS_PUBLIC_IP>`

Wait until both resolve:

```bash
nslookup wailearning.xyz
nslookup www.wailearning.xyz
```

Expected result:

- Both names resolve to your ECS public IP

## 9. Apply HTTPS

After HTTP is reachable from the public internet:

```bash
sudo certbot --nginx -d wailearning.xyz -d www.wailearning.xyz
```

Then verify renewal timer:

```bash
sudo systemctl status certbot.timer --no-pager
```

Expected result:

- Certbot completes successfully
- Nginx is automatically updated for TLS
- `certbot.timer` is enabled or active

## 10. Post-Deployment Acceptance Check

Run:

```bash
sudo bash scripts/post_deploy_check.sh
```

Then manually validate from a browser:

1. Open `https://wailearning.xyz/`
2. Confirm the admin login page loads
3. Log in with the bootstrap admin account
4. Open `https://wailearning.xyz/parent/`
5. Confirm the parent portal login page loads
6. Open `https://wailearning.xyz/health`
7. Confirm the API responds normally
8. As admin, open the system settings page and confirm LLM endpoint preset management is available
9. As teacher, open a course and confirm the LLM configuration dialog is available
10. Create a homework with auto-grading enabled, submit once as a student, and confirm the grading task transitions from queued/processing to success or failed

## 11. Frequently Used Operations

Restart backend:

```bash
sudo systemctl restart ddclass-backend
```

Reload Nginx:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

View backend logs:

```bash
sudo journalctl -u ddclass-backend -f
```

View Nginx logs:

```bash
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

## 12. Upgrade Procedure

When you update the code, **avoid a bare `git pull` on the server** if the machine may have local drift or tracking issues. Prefer aligning the checkout to the remote branch, then deploy (see **`docs/DEPLOY_GIT_ROBUSTNESS.md`** for rationale):

```bash
cd /opt/dd-class/source
GIT_BRANCH=main GIT_REMOTE=origin sudo bash scripts/redeploy.sh
# or: REPO_DIR=/opt/dd-class/source GIT_BRANCH=main sudo bash scripts/pull_and_deploy.sh
# (pull_and_deploy accepts BRANCH or GIT_BRANCH; if REPO_DIR is unset and /opt/dd-class/source is a git clone, that path is used by default.)
```

If the server clone has local modifications that block checkout, run once with **`GIT_RESET_WORKTREE_BEFORE_FETCH=1`** (backs up `git diff` under `/opt/dd-class/backups` by default). See **`docs/DEPLOY_GIT_ROBUSTNESS.md`**.

`redeploy.sh` runs the full stack (backend + frontends + nginx reload as configured). For a manual code-only refresh, mirror **`scripts/lib/git_sync_server.sh`**: explicit refspec **`git fetch <remote> refs/heads/<branch>:refs/remotes/<remote>/<branch>`**, then **`git checkout -B`** + **`git reset --hard`** + **`git clean -ffd`**, then `deploy_all.sh`.

If you uploaded files manually, replace the Git block with your preferred sync method.

## 13. Backup Procedure

Create a database backup:

```bash
sudo -u postgres pg_dump -Fc ddclass > /opt/dd-class/backups/ddclass-$(date +%F-%H%M%S).dump
```

Create a config and static backup:

```bash
sudo tar -czf /opt/dd-class/backups/ddclass-files-$(date +%F-%H%M%S).tar.gz \
  /opt/dd-class/shared \
  /var/www/wailearning.xyz
```

## 14. Rollback Procedure

If a deployment breaks after a code update:

1. Restore the previous code version in `/root/dd-class`
2. Re-run `sudo bash scripts/deploy_all.sh`
3. Re-run `sudo bash scripts/post_deploy_check.sh`

If the issue is database-related:

1. Stop the backend:

```bash
sudo systemctl stop ddclass-backend
```

2. Restore a PostgreSQL backup:

```bash
sudo -u postgres dropdb ddclass
sudo -u postgres createdb -O ddclass ddclass
sudo -u postgres pg_restore -d ddclass /opt/dd-class/backups/<backup-file>.dump
```

3. Start the backend again:

```bash
sudo systemctl start ddclass-backend
```

## 15. Common Failure Patterns

`502 Bad Gateway`

- Usually means the backend service is not running
- Check `sudo systemctl status ddclass-backend --no-pager`
- Check `sudo journalctl -u ddclass-backend -n 100 --no-pager`

`500 Internal Server Error` after login

- Usually means env or database settings are wrong
- Re-check `/opt/dd-class/shared/.env.production`
- Confirm `DATABASE_URL` matches the actual PostgreSQL password

Frontend page loads, but API calls fail

- Check browser network requests
- Confirm `https://wailearning.xyz/api/...` is reachable
- Check Nginx proxy config and backend health

`404` after refreshing a frontend route

- Re-check the installed Nginx config
- Confirm the server uses the repo's `nginx/wailearning.xyz.conf`

Certbot issuance fails

- Confirm DNS resolves to the ECS public IP
- Confirm port `80` is open in Alibaba Cloud security group
- Confirm local firewall is not blocking HTTP

## 16. Security Baseline

Before production traffic, confirm:

- SSH password login is disabled if you already use key login
- PostgreSQL is only listening locally
- Only ports `22`, `80`, and `443` are open externally
- `.env.production` is readable only by privileged users
- The admin bootstrap password is changed from a temporary setup value

## 17. Recommended Next Step

After first successful go-live, the next safest improvement is:

1. Create a dedicated Git repository for your modified version
2. Add scheduled PostgreSQL backups
3. Add application-level audit logs
4. Replace bootstrap table creation with formal migrations
