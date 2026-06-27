# GSAD — GPU 资源申请与分配

**Languages:** [English](README.md) · [简体中文](README.zh-CN.md)

自托管 GPU SSH 访问面板：用户申请访问，agent 开通账号，reporter 上报指标。

**技术栈：** Spring Boot 4 / Java 21 · Vue 3 + Vite · PostgreSQL 16 · Redis 7 · Traefik v3

| 我想… | 从这里开始 |
| ----- | ---------- |
| 生产部署 | [部署](#部署) |
| 本地试用（无 TLS） | [docs/local-prod.zh-CN.md](docs/local-prod.zh-CN.md) |
| 开发 UI + mock agent | [docs/dev.zh-CN.md](docs/dev.zh-CN.md) |
| 学生批量 onboarding（表格） | [Account preparation](#account-preparation表格--gsad--netbird) |

*运维 → [部署](#部署)。开发 → [docs/dev.zh-CN.md](docs/dev.zh-CN.md)。*

## 目录

- [前置条件](#前置条件)
- [部署](#部署)
- [Agent access & security](#agent-access--security)
- [部署后](#部署后)
  - [First admin](#first-admin)
  - [Account preparation](#account-preparation表格--gsad--netbird)
  - [Agent PSK](#agent-psk-per-gpu-host)
  - [Backup and restore](#backup-and-restore)
  - [Upgrades and health](#upgrades-and-health)
- [仓库结构](#仓库结构)
- [配置](#配置)
- [其他环境](#其他环境)
- [测试](#测试)
- [延伸阅读](#延伸阅读)

```mermaid
flowchart TB
  Browser(["Users / browser"])

  subgraph central ["Central host (Docker)"]
    Traefik["Traefik :443"]
    UI["Vue UI"]
    Backend["Backend"]
    Traefik --> UI
    Traefik -->|"HTTPS /api JWT"| Backend
  end

  subgraph data ["Data"]
    PG[(PostgreSQL)]
    RD[(Redis)]
  end

  subgraph agents ["GPU hosts"]
    Prov[account-provisioner]
    Rep[gpu-server-report]
  end

  Browser -->|"HTTPS :443"| Traefik
  Backend --> PG
  Backend --> RD
  Prov -->|"HTTP agent port /api/internal"| Backend
  Rep -->|"HTTP agent port /api/internal"| Backend
```

> [!NOTE]
> Agent 通过私网/VPN IP 上的 `BACKEND_AGENT_PORT` 以 HTTP 调用 `/api/internal/*`。Traefik 在 `:443` 上拦截这些路由。详见 [Agent access & security](#agent-access--security)。

## 前置条件

- Docker 与 Docker Compose

## 部署

1. 带子模块克隆：

```bash
git clone --recursive git@github.com:zeroDtree/server-manager.git
# 或普通 clone 后：
# git submodule update --init --recursive
```

2. 配置并启动 — 在运行 `secret.sh` 前于 `.env` 中设置 `GSAD_PUBLIC_HOST` 与 `ACME_EMAIL`：

```bash
cp .env.example .env
# 在 .env 中设置 GSAD_PUBLIC_HOST 与 ACME_EMAIL
./utils/secret.sh
docker compose -f compose.yaml -f dockers/compose.prod.yaml --profile prod up -d --build
```

3. 将 `GSAD_PUBLIC_HOST` 的 DNS 指向本机；开放 80、443 端口。Traefik 终结 HTTPS（Let's Encrypt）。
4. 等待 backend 健康：

```bash
curl -sS "https://${GSAD_PUBLIC_HOST}/actuator/health"
# expect: {"status":"UP",...}
```

5. [创建首个管理员](#first-admin)。
6. **Admin → Import servers**（CSV）；[派生 agent PSK](docs/agent-psk.zh-CN.md)；在各 GPU 主机部署 [server-agent](server-agent/)。
7. **Admin → Import users**。
8. 将 `BACKEND_AGENT_PORT`（默认 `:8080`）限制为 GPU 主机 / VPN 网段 — 切勿暴露到公网。
9. 启用[备份](docs/backup.zh-CN.md)；定期测试恢复。

## Agent access & security

**两条入口**

| 路径            | 受众                 | 协议  | 路由                                                   |
| --------------- | -------------------- | ----- | ------------------------------------------------------ |
| 用户 / 浏览器   | HTTPS `:443` Traefik | HTTPS | `/`、`/api/*`（JWT）                                   |
| GPU agent       | `BACKEND_AGENT_PORT` | HTTP  | `/api/internal/*`（`X-Agent-Server-Id`、`X-Agent-PSK`） |

**为何用 HTTP 而非公网 HTTPS？**

- Traefik 在 `:443` 上按设计拦截 `/api/internal/*`。
- Agent 使用中心主机私网/VPN IP（如 NetBird），而非 `https://${GSAD_PUBLIC_HOST}`。
- 避免每台主机管理 TLS 证书；认证为基于 `AGENT_MASTER_SECRET` 派生的 per-server HMAC。

**网络要求**

- 将 `BACKEND_AGENT_PORT`（默认 `:8080`）限制为仅 GPU 主机 — NetBird mesh CIDR、私网 LAN 或防火墙白名单。
- `BACKEND_AGENT_BIND` 设为 `127.0.0.1` 或 RFC1918 地址；启动时拒绝 `0.0.0.0` 与公网 IP。

> [!WARNING]
> 勿将 `:8080` 暴露到公网。HTTP 明文传输 agent 凭据。

> [!IMPORTANT]
> 在**仅 backend** 使用足够长的随机 `AGENT_MASTER_SECRET`；backend 拒绝默认值。每台 GPU 主机派生 `AGENT_PSK` — 见 [Agent PSK (per GPU host)](docs/agent-psk.zh-CN.md)。切勿将 `AGENT_MASTER_SECRET` 部署到 GPU 主机。

**Agent 配置：** `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` — 见 [server-agent/README.md](server-agent/README.md)。

## 部署后

### First admin

Flyway 仅含 schema，**无预置管理员**。在 `backend` 与 `postgres` 健康后，用 [`create-prod-admin.sh`](utils/create-prod-admin.sh) 创建首个管理员。

在仓库根目录：

```bash
ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh
```

或内联设置密码（**不要**将 bootstrap 密码写入 `.env`）：

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='your-strong-password' ./utils/create-prod-admin.sh
```

脚本**幂等**：若已有管理员则直接退出。dev/mock 后需干净 bootstrap 时，在[本地 HTTP 栈](docs/local-prod.zh-CN.md)执行 [`down -v`](docs/local-prod.zh-CN.md#reset-clean-db)，再 `up` 并重新运行本脚本。

可选环境变量：`ADMIN_LINUX_USERNAME`（默认 `gsadadmin`）、`ADMIN_DISPLAY_NAME`（默认 `Admin`）。

验证登录：

```bash
curl -sS -X POST "https://${GSAD_PUBLIC_HOST}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<your-password>"}'
```

在[本地 HTTP 栈](docs/local-prod.zh-CN.md)上使用 `http://localhost/api/auth/login`。

通过侧栏 **Account → Change password**（或 `POST /api/auth/change-password`）修改 bootstrap 密码。

通过 **Admin → Import users** 导入用户。必填列：`email`、`linux_username`、`initial_password`（至少 8 位）。可选：`display_name`、`student_id`、`cohort`、`roles`。初始密码须通过安全渠道分发 — API 不会返回。管理员可在 **Admin → Users** 重置非管理员账号的登录密码。

### Account preparation（表格 → GSAD + NetBird）

[`account_prepare/`](account_prepare/) 负责表格批量 onboarding：SQLite 账本、`data/account_prepare/` 下导入 CSV、NetBird/GSAD 对账与统一凭据邮件。向学生收集哪些字段见 [docs/info.zh-CN.md](docs/info.zh-CN.md)；完整流程见 [account_prepare/README.md](account_prepare/README.md)（`prepare-accounts` → NetBird 导入 → GSAD UI 导入 → `reconcile-accounts` → `notify-accounts`）。

### Agent PSK (per GPU host)

每台 GPU agent 使用从仅 backend 持有的 `AGENT_MASTER_SECRET` 派生的 per-server HMAC。在可信机器上派生 `AGENT_PSK` 并部署到 agent — 见 [docs/agent-psk.zh-CN.md](docs/agent-psk.zh-CN.md)。

### Backup and restore

定时 Postgres 备份、日志轮转与恢复 — 见 [docs/backup.zh-CN.md](docs/backup.zh-CN.md)。

### Upgrades and health

- Backend 健康：`/actuator/health`
- Agent 健康：`:9091`（provisioner）、`:9092`（reporter）

```bash
curl -sS "https://${GSAD_PUBLIC_HOST}/actuator/health"
# expect: {"status":"UP",...}
```

升级中心栈：

```bash
git pull && git submodule update --init --recursive && \
  docker compose -f compose.yaml -f dockers/compose.prod.yaml --profile prod up -d --build
```

升级 GPU 主机 agent：`git pull && sudo ./deploy/install.sh`。

上线前预检：使用[本地 HTTP 栈](docs/local-prod.zh-CN.md)在真实 DNS 与 TLS 之前验证镜像与路由。

## 仓库结构

Git 子模块 — clone 后运行 `git submodule update --init --recursive`。

| 路径                                | 职责                                                                                     |
| ----------------------------------- | ---------------------------------------------------------------------------------------- |
| [gsad-backend](gsad-backend/)       | REST API、Flyway、internal agent 路由                                                    |
| [gsad-frontend](gsad-frontend/)     | Vue UI                                                                                   |
| [server-agent](server-agent/)       | account-provisioner + gpu-server-report（GPU 主机 systemd）                              |
| [netbird-manage](netbird-manage/)   | NetBird CLI（`user-manage`、`policy-manage`）— 子模块                                    |
| [account_prepare](account_prepare/) | 登记表格 → GSAD/NetBird CSV 与凭据邮件                                                   |
| [dockers](dockers/)                 | Compose、Dockerfile、开发 mock agent（`dockers/mocks/`）                                 |
| [utils](utils/)                     | 仓库级运维脚本（`.env` 密钥、`create-prod-admin`、agent PSK 派生、DB 备份、systemd 单元） |

## 配置

部署需在 `.env` 中设置 `GSAD_PUBLIC_HOST` 与 `ACME_EMAIL`。运行 [`secret.sh`](utils/secret.sh) 为其余项生成 ≥32 字符随机密钥。已设置的键不会被覆盖。完整说明见 [`.env.example`](.env.example)。

| 变量                             | 必填 | 默认           | 说明                                                                 |
| -------------------------------- | ---- | -------------- | -------------------------------------------------------------------- |
| `SPRING_PROFILES_ACTIVE`         | 是   | `dev`          | 配合 `compose.prod.yaml` 时为 `prod`                                 |
| `GSAD_PUBLIC_HOST`               | 是   | —              | Traefik 主机名与 DNS                                                 |
| `ACME_EMAIL`                     | 是   | —              | Let's Encrypt 邮箱                                                   |
| `BACKEND_AGENT_PORT`             | 否   | `8080`         | Agent internal API 主机端口                                          |
| `BACKEND_AGENT_BIND`             | 否   | `127.0.0.1`    | Loopback 或 RFC1918；见 [Agent access & security](#agent-access--security) |
| `CREDENTIALS_ENCRYPTION_KEY`     | 是   | —              | SSH 凭据静态加密 AES 密钥（≥32 字符）                                |
| `AGENT_MASTER_SECRET`            | 是   | —              | 仅 backend；经 [docs/agent-psk.zh-CN.md](docs/agent-psk.zh-CN.md) 派生 PSK |
| `JWT_SECRET`                     | 是   | —              | JWT 签名密钥（≥32 字符）                                             |
| `DB_PASSWORD` / `REDIS_PASSWORD` | 是   | —              | 数据存储密码                                                         |
| `CORS_ALLOWED_ORIGINS`           | 否   | 空             | UI 与 API 经 Traefik 同域时通常留空                                  |

> [!WARNING]
> 勿使用 `.env.example` 占位值。运行 [`secret.sh`](utils/secret.sh) 或手动设置强随机值。生产环境禁用 Swagger；agent 在私网 HTTP 端口使用派生 PSK + `X-Agent-Server-Id` 认证。

## 其他环境

| 环境                     | 文档                                         |
| ------------------------ | -------------------------------------------- |
| 开发（Vite + mock agent） | [docs/dev.zh-CN.md](docs/dev.zh-CN.md)       |
| 本地无 TLS 栈            | [docs/local-prod.zh-CN.md](docs/local-prod.zh-CN.md) |

## 测试

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```

许可证：[LICENSE](LICENSE)

## 延伸阅读

- [docs/agent-psk.zh-CN.md](docs/agent-psk.zh-CN.md) — 每台 GPU 主机 PSK 派生
- [docs/backup.zh-CN.md](docs/backup.zh-CN.md) — 备份、恢复与日志轮转
- [account_prepare/README.md](account_prepare/README.md) — 表格 onboarding 流程
- [gsad-backend/README.md](gsad-backend/README.md) — API 路由、schema、Flyway
- [server-agent/README.md](server-agent/README.md) — GPU 主机 agent 安装
- [gsad-frontend/openapi/openapi.json](gsad-frontend/openapi/openapi.json) — OpenAPI 规范（已入库）
