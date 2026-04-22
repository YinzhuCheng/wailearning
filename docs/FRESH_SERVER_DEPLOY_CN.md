# 空机器首次部署（指令流）

本文说明**为何**按错误顺序会失败，并给出**从 0 到可访问**的推荐步骤。与 `DEPLOY.md`、`RUNBOOK_ALIYUN.md` 一致，更强调顺序与常见坑。

## 一、最初那套指令为何出错

1. **未先初始化 PostgreSQL**  
   `scripts/deploy_all.sh` 只负责同步代码、装依赖、启动 `ddclass-backend` 等，**不会**创建数据库用户 `ddclass` 或设置密码。  
   若跳过 `init_db.sql`，`app.bootstrap` 在 `ExecStartPre` 里连库时会报：  
   `FATAL: password authentication failed for user "ddclass"`（或用户/库不存在）。

2. **评论写「自动初始化 DB」易误导**  
   实际必须**手工**执行 `scripts/init_db.sql`，且 `-v db_password=...` 必须与 `.env.production` 里 `DATABASE_URL` 的密码**完全一致**。

3. **`sudo -u postgres psql` 在 `/root/...` 下偶发告警**  
   `postgres` 系统用户不能 `cd` 进 root 家目录，会出现 `could not change directory ... Permission denied`，一般**不影响** SQL 已执行。规避：先 `cd /tmp` 再跑 `psql`。

4. **公网健康检查出现 301**  
   配置 HTTPS 后，用 `http://域名/...` 访问常被 Nginx **301 到 https**，未跟随重定向时看起来像「失败」。应用 `https://` 或 `curl -L`。

---

## 二、新机器推荐指令流（请替换尖括号与密码）

在 **Ubuntu 22.04** 等系统上，以 `root` 或 `sudo` 执行。假设代码在 `/root/wailearning`，域名以 `wailearning.xyz` 为例。

### 0. 准备

- 云安全组放行：**22、80、443**。
- 本地生成强密钥备用：`openssl rand -hex 32`

### 1. 拉代码

```bash
cd /root
git clone https://github.com/YinzhuCheng/wailearning.git wailearning
cd /root/wailearning
chmod +x scripts/*.sh
```

### 2. 装系统依赖（Nginx、PostgreSQL、Node 等）

```bash
sudo bash scripts/setup_server.sh
```

### 3. 写生产环境（把密码改成你自己的强密码）

```bash
sudo install -m 640 /root/wailearning/.env.production /opt/dd-class/shared/.env.production
sudo nano /opt/dd-class/shared/.env.production
```

至少保证：

- `DATABASE_URL=postgresql://ddclass:<与下面 init_db 相同密码>@127.0.0.1:5432/ddclass`
- `SECRET_KEY=<openssl rand -hex 32 生成的值>`
- `BACKEND_CORS_ORIGINS`、`TRUSTED_HOSTS` 含你的域名
- 无 `CHANGE_ME` 残留

示例（**勿照抄弱密码**）：

```dotenv
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql://ddclass:YOUR_DB_PASSWORD@127.0.0.1:5432/ddclass
SECRET_KEY=YOUR_LONG_RANDOM_SECRET
BACKEND_CORS_ORIGINS=https://wailearning.xyz,https://www.wailearning.xyz
TRUSTED_HOSTS=wailearning.xyz,www.wailearning.xyz,127.0.0.1,localhost
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=YOUR_ADMIN_PASSWORD
INIT_DEFAULT_DATA=true
```

```bash
sudo chown root:ddclass /opt/dd-class/shared/.env.production
sudo chmod 640 /opt/dd-class/shared/.env.production
```

### 4. 初始化数据库（在 deploy 之前，且密码与 DATABASE_URL 一致）

```bash
cd /tmp
cp /root/wailearning/scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name='ddclass' \
  -v db_user='ddclass' \
  -v db_password='YOUR_DB_PASSWORD' \
  -f /tmp/init_db.sql
```

### 5. 一键部署（前后端 + systemd）

```bash
cd /root/wailearning
sudo bash scripts/deploy_all.sh
```

### 6. 本机验证

```bash
sudo systemctl status ddclass-backend --no-pager
curl -fsS http://127.0.0.1:8001/api/health
```

### 7. 部署后检查

```bash
# 若已上 HTTPS，建议跟重定向
sudo APP_URL=https://wailearning.xyz API_HEALTH_URL="https://wailearning.xyz/health" bash scripts/post_deploy_check.sh
```

### 8. DNS 与 HTTPS（对公网访问必做）

在 DNS 控制台将 `wailearning.xyz`、`www` 指到 ECS 公网 IP，解析生效后：

```bash
sudo certbot --nginx -d wailearning.xyz -d www.wailearning.xyz
```

---

## 三、顺序小结

`setup_server` → **写好 `.env.production`** → **`init_db.sql`（密码一致）** → `deploy_all` → 本机 `curl` → DNS + `certbot` → 浏览器访问 `https://你的域名/`。

忘记第 4 步或密码不一致，是最常见的首次部署失败原因。
