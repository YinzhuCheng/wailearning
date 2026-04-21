# 阿里云服务器安全升级要点（数据保护版）

本文档面向已经在阿里云 ECS 上运行的 BIMSA-CLASS 系统，重点说明：

- **升级代码时哪些目录和数据绝对不能直接删**
- **怎样在升级前先保护原始数据**
- **怎样在保留教师、学生、作业、资料、评分、附件等数据资产的前提下更新代码**

如果你只想看简洁版部署说明，请阅读 `DEPLOY.md`。  
如果你想看首次上线/演练/回滚流程，请阅读 `RUNBOOK_ALIYUN.md`。  
如果你希望直接参考一个脚本模板，请看 `scripts/example_safe_upgrade_aliyun.sh`。

---

## 1. 当前系统中最重要的数据资产

升级前要先明确：**代码不是最重要的，数据才是最重要的**。

### 1.1 数据库资产

这些数据通常保存在 PostgreSQL 中：

- 管理员 / 教师 / 班主任 / 学生账户
- 班级、课程、学期、成绩、考勤
- 作业定义
- 作业提交汇总、提交历史、评分候选分、评分任务
- 课程级 LLM 配置、端点预设、token 记账
- 通知、资料、积分相关数据

### 1.2 文件资产

这些数据通常保存在共享 uploads 目录中：

- 作业附件
- 学生提交附件
- 课程资料附件
- 通知附件

按照当前部署脚本，推荐共享目录为：

- `/opt/dd-class/shared/uploads`

---

## 2. 可以假定的升级前目录结构

以下目录是本文档默认假定的现网目录：

```text
/opt/dd-class/
├── source/                     # 当前运行代码
├── venv/                       # Python 虚拟环境
├── shared/
│   ├── .env.production         # 生产环境配置
│   └── uploads/                # 共享附件目录
│       └── attachments/
└── backups/                    # 备份目录

/var/www/wailearning.xyz/
├── admin/                      # 管理端前端产物
└── parent/                     # 家长端前端产物
```

---

## 3. 升级时最重要的“数据保护原则”

### 原则 A：不要把升级理解成“重装系统”

升级代码时：

- **不要删除 PostgreSQL 数据库**
- **不要删除 `/opt/dd-class/shared/uploads`**
- **不要删除 `/opt/dd-class/shared/.env.production`**

真正需要更新的是：

- `/opt/dd-class/source`
- Python 依赖
- 前端构建产物
- systemd / nginx 配置（如有变更）

### 原则 B：先备份，再升级

至少备份这三样：

1. 数据库 dump
2. `shared/uploads`
3. `shared/.env.production`

如果升级后出现问题，可以优先回滚：

- 代码
- 配置
- 数据库
- 上传文件

### 原则 C：上传目录必须保持“共享目录”语义

当前系统的附件安全依赖“代码目录”和“共享目录”分离：

- 代码目录可以被新版本覆盖
- 共享 uploads 必须独立存在

所以要确保：

- `UPLOADS_DIR=/opt/dd-class/shared/uploads`

不要把上传目录重新指回仓库内的 `uploads/`，否则更新代码时更容易误伤原始附件。

### 原则 D：LLM worker 只允许一个 leader

当前作业自动评分 worker 仍然是：

- **数据库驱动**
- **进程内 worker**
- **依靠配置选择 leader**

因此多实例部署时必须保证：

- 只有一个实例设置 `LLM_GRADING_WORKER_LEADER=true`

其他实例应设为：

- `LLM_GRADING_WORKER_LEADER=false`

否则可能出现重复消费或任务状态混乱。

### 原则 E：生产环境默认不要开放公开注册

建议保持：

```dotenv
ALLOW_PUBLIC_REGISTRATION=false
```

这样升级时不会因为新版本切换后暴露不受控的注册入口。

---

## 4. 升级前必须检查的项目

在执行部署前，建议先确认：

### 4.1 数据库

```bash
sudo systemctl status postgresql --no-pager
sudo -u postgres psql -d ddclass -c '\conninfo'
```

### 4.2 后端服务

```bash
sudo systemctl status ddclass-backend --no-pager
curl -fsS http://127.0.0.1:8001/health
```

### 4.3 uploads 共享目录

```bash
sudo ls -lah /opt/dd-class/shared/uploads
sudo ls -lah /opt/dd-class/shared/uploads/attachments | tail
```

### 4.4 生产配置

```bash
sudo grep -E 'UPLOADS_DIR|ALLOW_PUBLIC_REGISTRATION|ENABLE_LLM_GRADING_WORKER|LLM_GRADING_WORKER_LEADER' /opt/dd-class/shared/.env.production
```

建议确认输出至少包含：

```dotenv
UPLOADS_DIR=/opt/dd-class/shared/uploads
ALLOW_PUBLIC_REGISTRATION=false
ENABLE_LLM_GRADING_WORKER=true
LLM_GRADING_WORKER_LEADER=true
```

---

## 5. 升级前建议备份的内容

### 5.1 数据库备份

```bash
sudo -u postgres pg_dump -Fc ddclass > /opt/dd-class/backups/ddclass-$(date +%F-%H%M%S).dump
```

### 5.2 共享目录备份

```bash
sudo tar -czf /opt/dd-class/backups/ddclass-shared-$(date +%F-%H%M%S).tar.gz \
  /opt/dd-class/shared
```

### 5.3 当前代码快照备份（可选但强烈建议）

```bash
sudo tar -czf /opt/dd-class/backups/ddclass-source-$(date +%F-%H%M%S).tar.gz \
  /opt/dd-class/source
```

---

## 6. 安全升级流程（推荐）

推荐顺序：

1. 备份数据库
2. 备份共享目录
3. 备份当前代码目录（可选）
4. 拉取新代码
5. 运行部署脚本
6. 做 post-deploy 检查
7. 验证：
   - 管理端登录
   - 家长端访问
   - 教师课程页 LLM 配置
   - 学生提交与评分状态

---

## 7. 当前架构下，哪些操作最危险

以下操作**最容易造成数据损坏或丢失**：

### 危险操作 1：删掉 shared 目录

例如：

```bash
sudo rm -rf /opt/dd-class/shared
```

会直接损坏：

- uploads
- 生产配置
- 作业/资料/通知等附件关联的实际文件

### 危险操作 2：重建数据库但不恢复备份

例如：

```bash
sudo -u postgres dropdb ddclass
sudo -u postgres createdb ddclass
```

会直接丢失：

- 教师学生信息
- 原始作业
- 评分历史
- LLM 配置

### 危险操作 3：把 UPLOADS_DIR 改回代码目录

如果配置成：

```dotenv
UPLOADS_DIR=/opt/dd-class/source/uploads
```

则后续代码同步、覆盖、清理时更容易误伤附件。

### 危险操作 4：多实例同时启用 worker leader

会增加作业评分任务重复消费、任务状态混乱的风险。

---

## 8. 建议的回滚思路

如果升级失败，回滚优先级建议如下：

### 8.1 代码回滚

优先恢复上一版本代码，然后重新执行部署脚本。

### 8.2 配置回滚

如果是配置问题，优先恢复：

- `/opt/dd-class/shared/.env.production`

### 8.3 数据库回滚

如果发现 schema patch 或数据兼容逻辑出错，再恢复 dump：

```bash
sudo systemctl stop ddclass-backend
sudo -u postgres dropdb ddclass
sudo -u postgres createdb -O ddclass ddclass
sudo -u postgres pg_restore -d ddclass /opt/dd-class/backups/<backup-file>.dump
sudo systemctl start ddclass-backend
```

### 8.4 共享文件回滚

如果附件目录损坏，再恢复 shared 备份包。

---

## 9. 示例脚本

仓库中已提供一个可参考的安全升级脚本样例：

- `scripts/example_safe_upgrade_aliyun.sh`

这个脚本示例会：

- 自动在升级前备份数据库
- 打包共享目录
- 可选备份当前 source 目录
- 拉取指定分支代码
- 调用现有部署脚本完成升级
- 最后执行 post-deploy 检查

> 注意：它是**示例脚本**，请先按你们自己的机器目录、数据库名、分支策略、systemd 服务名进行调整，再上线使用。

