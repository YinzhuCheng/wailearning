# 管理员账号与密码设置说明

本仓库在**首次启动后端**时，由 `app/bootstrap.py` 中的 `seed_default_admin()` 根据**环境变量**创建**系统管理员**用户（角色为 `admin`），前提是 `INIT_DEFAULT_DATA` 为 `true`（默认值）。

## 1. 通过环境变量设置（推荐：部署前 / 空库首次启动前）

在运行后端的**同一环境**中设置下列变量（可在项目根目录的 `.env` 文件中配置；`app/config.py` 使用 `pydantic_settings`，会读取该文件）：

| 变量名 | 含义 | 代码中的默认示例 |
|--------|------|------------------|
| `INIT_ADMIN_USERNAME` | 管理员登录用户名 | `admin` |
| `INIT_ADMIN_PASSWORD` | 管理员初始密码 | `ChangeMe123!` |
| `INIT_ADMIN_REAL_NAME` | 显示名称 | `System Administrator` |

示例（请把密码改为强密码）：

```env
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=你的强密码
INIT_ADMIN_REAL_NAME=System Administrator
```

**重要行为：**

- 仅在**数据库中尚不存在**该 `INIT_ADMIN_USERNAME` 时，才会创建管理员并写入哈希后的密码。
- 若该用户名**已存在**，启动时**不会**用环境变量覆盖已有密码，控制台会提示管理员已存在。

## 2. 已有系统中修改密码

- **方式 A**：使用仓库内脚本 `scripts/reset_user_password.sh`（面向典型服务器路径，可通过 `REPO_DIR`、`VENV_DIR`、`ENV_FILE` 覆盖）：
  ```bash
  bash scripts/reset_user_password.sh <用户名> <新密码>
  ```
- **方式 B**：在管理端登录后，若产品提供“修改密码”能力，通过接口 `/auth/change-password` 修改（以实际前端与权限为准）。

生产环境上也可参考 `scripts/set-password.sh` 中通过 Python 在数据库中创建或更新 `admin` 用户并设置哈希密码的思路（需按实际安装路径与虚拟环境调整）。

## 3. 相关配置项

- `INIT_DEFAULT_DATA`：若为 `false`，**不会**执行包含默认管理员在内的种子数据逻辑（见 `app/bootstrap.py` 中 `bootstrap()`）。
- 生产部署示例中亦出现与上述相同的环境变量名，例如仓库根目录的 `.env.production` 模板、以及 `RUNBOOK_ALIYUN.md` 中的说明。

## 4. 代码与文档位置（便于自行核对）

- 默认值与变量名定义：`app/config.py`（`INIT_ADMIN_*`）
- 创建逻辑：`app/bootstrap.py`（`seed_default_admin`）
- 本地说明中可能出现与默认配置不一致的“演示账户”表述，请以**实际 `.env` / 环境变量**和**数据库**为准。

---

*本文档仅汇总本仓库中管理员相关的设置方式，不修改其他代码或说明文件。*
