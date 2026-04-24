# 生产部署常见踩坑与「公网 IP + HTTP(80)」线（中文）

本文记录真实部署中容易反复出现的问题，并给出**无域名、仅用公网 IP 与 80 端口、HTTP** 时的**标准复用流程**（从空机器开始）。与 `DEPLOY.md`、`docs/FRESH_SERVER_DEPLOY_CN.md` 互补；若已有域名与 HTTPS，仍以 `RUNBOOK_ALIYUN.md` 为主。

---

## 一、访问模式先定好：「IP + HTTP」≠「域名 + HTTPS」

- **当前模式**（无域名、未上证书）：在浏览器用 `http://<公网IP>/...`，走 **80** 端口，**HTTP**。地址栏会提示“不安全”是**正常现象**。
- **不是** `https://`，也**不是**在没解析域名时去跑 `certbot`；证书目录不存在时，仓库会选用 **HTTP 版** Nginx 模板（`nginx/wailearning.xyz.http.conf`），`deploy_frontend.sh` / `deploy_parent_portal.sh` 中已有判断逻辑。
- 有域名并解析到本机、需要加密时，再改环境变量并执行 `certbot`，与本文场景分开，避免按「已有证书」的路径排查。

---

## 二、排障时容易搞错的几个点（规范化表述）

### 1. 后端监听位置：不要从公网直连 8001

- 服务绑定在 **`127.0.0.1:8001`**，仅供本机或 **Nginx 反代**使用。
- **正确外网入口**：`http://<公网IP>/`（即 **80** 端口），由 Nginx 将 `/api/` 等路径转发到后端。
- 本机/SSH 上自检可用：`curl http://127.0.0.1:8001/api/health`。除非清楚风险，**不要在安全组中向全网开放 8001**。

### 2. systemd 服务名要用真实值

- 后端服务名为 **`ddclass-backend.service`**（`systemctl restart ddclass-backend`），文档里若出现 `your_backend_service` 等仅为占位，照抄会失败。

### 3. Nginx：少改 `default`、多走仓库模板

- **不要**在 `/etc/nginx/sites-enabled/default` 里**再塞一个**与原有配置重复的 `location /`，否则易出现 **`duplicate location "/"`**。
- **不要**把备份文件（如 `default.bak`）放在 **`sites-enabled/`** 下，Nginx 会一并加载，可能触发 **`duplicate default server`** 等冲突。备份应放在家目录或 `/root/` 等非加载目录。
- `nginx -t` 失败时，**reload 不会生效**，有时主进程仍显示为 running，**旧配置继续生效**；以 `nginx -t` 和 `error.log` 为准，不要仅凭 `systemctl status nginx` 判断新规则已加载。
- **优先**使用本仓库的 **`scripts/deploy_frontend.sh`**、**`scripts/deploy_parent_portal.sh`**：它们会构建前端、同步静态资源、安装**仓库自带**的站点配置、在 Debian/Ubuntu 上**移除** `sites-enabled/default` 的冲突链接，并 `nginx -t` 后 **reload**。**手工大改**系统 Nginx 应作为最后手段。

### 4. 「能打开 JSON」≠「网站已好」

- 若浏览器里看到的是 **`{"message":"...","status":"running",...}`** 这类根路径 JSON，常表示请求打到了**后端**或反代到 API，**不是**已部署好的**前端 SPA 首页**。
- 前端的“部署成功”通常表现为：`/` 返回 **HTML 文档**（或构建后的 `index.html`），且静态资源在 **`/var/www/wailearning.xyz/admin`**；家长端在 **`/var/www/.../parent`**，路径 **`/parent/`**。

### 5. 有 `package.json` 不等于已构建

- 仅克隆仓库、或只起后端，**不会**生成 `frontend/dist`、**`parent-portal/dist`**。必须跑 **`npm ci` + `npm run build`**（或直接用上述 deploy 脚本）。没有 **dist** 时，Nginx 无法提供完整前端，容易出现“只看见 API/空白/错误页”的误判。

### 6. 数据库与 `.env` 的对应关系

- 首次部署**必须先**执行 `scripts/init_db.sql`，且 **`db_password` 与 `DATABASE_URL` 中密码一致**；见 `FRESH_SERVER_DEPLOY_CN.md`。未初始化或密码不一致时，`ddclass-backend` 在 `app.bootstrap` 阶段会失败。

### 7. 仅用公网 IP 时：环境变量要带上 IP

- 后端启用 **`TrustedHostMiddleware`**。若只配置了域名、未在 **`TRUSTED_HOSTS`** 中写入**公网 IP**，通过 `http://公网IP` 访问时可能出现 **400 Invalid host header**。
- **`BACKEND_CORS_ORIGINS`** 中应包含 `http://<公网IP>`，以便浏览器在 IP 访问时通过 CORS 检查（与前端开发/预览端口视情况追加）。

---

## 三、「空机器 + 公网 IP + HTTP」可复制命令流

以下假定：**Ubuntu 22.04** 类系统、有 **root/ sudo**、安全组已放行 **22 与 80**；代码放在 **`/root/wailearning`**。请把所有 **`YOUR_...`** 换成你自己的值；**`47.x.x.x`** 仅为示例，**务必换成你的 ECS 公网 IP**。

```bash
# 0) 公网 IP（只用于下文替换，勿提交到仓库）
export ECS_PUBLIC_IP='47.242.58.29'   # 改成你的
```

```bash
# 1) 拉代码
cd /root
git clone https://github.com/YinzhuCheng/wailearning.git wailearning
cd /root/wailearning
chmod +x scripts/*.sh
```

```bash
# 2) 系统依赖
sudo bash scripts/setup_server.sh
```

```bash
# 3) 生产环境：数据库密码、SECRET_KEY 自行生成；TRUSTED/CORS 必须能覆盖「公网 IP 访问」
sudo install -m 640 /root/wailearning/.env.production /opt/dd-class/shared/.env.production
sudo nano /opt/dd-class/shared/.env.production
# 建议至少（把 YOUR_DB_PASSWORD 与第 4 步一致；把 IP 换成 ${ECS_PUBLIC_IP}）:
#   DATABASE_URL=postgresql://ddclass:YOUR_DB_PASSWORD@127.0.0.1:5432/ddclass
#   SECRET_KEY=<openssl rand -hex 32>
#   TRUSTED_HOSTS=${ECS_PUBLIC_IP},127.0.0.1,localhost
#   BACKEND_CORS_ORIGINS=http://${ECS_PUBLIC_IP},http://127.0.0.1,http://127.0.0.1:3000,http://127.0.0.1:5174
# 无 CHANGE_ME 后：
sudo chown root:ddclass /opt/dd-class/shared/.env.production
sudo chmod 640 /opt/dd-class/shared/.env.production
```

```bash
# 4) 初始化 PostgreSQL（与 DATABASE_URL 密码一致；在 /tmp 执行避免 cwd 权限告警）
cd /tmp
cp /root/wailearning/scripts/init_db.sql /tmp/init_db.sql
chmod 644 /tmp/init_db.sql
sudo -u postgres psql \
  -v db_name='ddclass' \
  -v db_user='ddclass' \
  -v db_password='YOUR_DB_PASSWORD' \
  -f /tmp/init_db.sql
```

```bash
# 5) 全量部署（含后端、拉依赖、起 systemd；会 build 前后端但依赖项目脚本，见 6 若需单独重跑）
cd /root/wailearning
sudo bash scripts/deploy_all.sh
```

```bash
# 6) 无证书时，确认仅用 HTTP 模板 + 建出 dist（若 5 未完整成功，可单独重跑）
cd /root/wailearning
sudo bash scripts/deploy_frontend.sh
sudo bash scripts/deploy_parent_portal.sh
# deploy_frontend 在无 /etc/letsencrypt/.../fullchain.pem 时安装的是 wailearning.xyz.http.conf
```

```bash
# 7) 本机与 systemd 检查
sudo systemctl status ddclass-backend --no-pager
curl -fsS "http://127.0.0.1:8001/api/health"
sudo nginx -t
```

在**能访问该服务器的浏览器**中（用真实公网 IP 替换）：

- 管理端首页：`http://<ECS_PUBLIC_IP>/`
- 家长端：`http://<ECS_PUBLIC_IP>/parent/`
- 经 Nginx 的健康检查：`http://<ECS_PUBLIC_IP>/health`
- 直连后端（**仅**在服务器上或经 SSH 隧道，用于排障）：`http://127.0.0.1:8001/api/health`

**判断「IP + HTTP 全链路 OK」的参考**：`/health` 为 200，根路径 `/` 为 **HTML** 而非整段 **API JSON**；可再打开 `/parent/` 为页面而非 404。

---

## 四、和「有域名 + HTTPS」的衔接

- 购买域名、DNS 指向本机后，在 `.env.production` 的 **`TRUSTED_HOSTS` / `BACKEND_CORS_ORIGINS`** 中加入域名，再按 `RUNBOOK_ALIYUN.md` 执行 `certbot`。成功后 `deploy_*.sh` 若检测到 Let’s Encrypt 证书，会切到 **HTTPS 模板**（`nginx/wailearning.xyz.conf`）。

---

## 五、精简检查清单（下次复用）

| 步骤 | 检查项 |
|------|--------|
| 模式 | 确认为 **IP + HTTP(80)**，**未**提前跑 **certbot**（无域名/无证书时） |
| 安全组 | 放行 **22、80**（上 HTTPS 后再开 **443**） |
| 库 | 已跑 **init_db.sql**，密码与 **DATABASE_URL** 一致 |
| 服务名 | 使用 **ddclass-backend** |
| 入口 | 外网走 **80**，**不要**把 **8001** 暴露给公网（除非知悉风险） |
| 环境 | **TRUSTED_HOSTS** / **CORS** 含**公网 IP** |
| 前端 | 存在 **dist**；优先 **deploy_frontend.sh** + **deploy_parent_portal.sh** |
| Nginx | 优先**仓库模板**；**勿**在 **sites-enabled** 里堆 **default.bak**；**勿**重复 **location /** |
| 成功现象 | **/** 为 **HTML**；**/api/health** 为 **200**；不是只有根路径 JSON 就当「网站已上线」 |

更通用的空机流程（含域名与 DNS）见 **docs/FRESH_SERVER_DEPLOY_CN.md**。
