# GSAD — GPU Server Access Dashboard

<p align="left">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

[![Java](https://img.shields.io/badge/Java-21-orange.svg)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.0-green.svg)](https://spring.io/projects/spring-boot)
[![Vue](https://img.shields.io/badge/Vue-3.x-42b883.svg)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-Latest-646cff.svg)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![Traefik](https://img.shields.io/badge/Traefik-v3-24A1C1.svg)](https://traefik.io/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)

> 自托管 GPU SSH 访问面板：用户申请、agent 开通账号、上报指标。

## Quick Links

| [🚀 生产部署](#部署) | [💻 本地试用（无 TLS）](docs/local-prod.zh-CN.md) | [🛠️ UI 与 Agent 开发](docs/dev.zh-CN.md) | [👥 学生 onboarding](account_prepare/README.md) |
| :---: | :---: | :---: | :---: |

---

```mermaid
flowchart TB
  Browser(["Users / Browser"])

  subgraph central ["Central Host (Docker)"]
    Traefik["Traefik :443"]
    UI["Vue UI"]
    Backend["Backend (Spring Boot)"]
    Traefik --> UI
    Traefik -->|"HTTPS /api JWT"| Backend
  end

  subgraph data ["Data Layers"]
    PG[("PostgreSQL 16")]
    RD[("Redis 7")]
  end

  subgraph agents ["GPU Hosts (Agents)"]
    Prov["account-provisioner"]
    Rep["gpu-server-report"]
  end

  Browser -->|"HTTPS :443"| Traefik
  Backend --> PG
  Backend --> RD
  Prov -->|"HTTP BACKEND_AGENT_PORT /api/internal"| Backend
  Rep -->|"HTTP BACKEND_AGENT_PORT /api/internal"| Backend

  classDef central fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
  classDef data fill:#efebe9,stroke:#795548,stroke-width:2px
  classDef agents fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
  class Traefik,UI,Backend central
  class PG,RD data
  class Prov,Rep agents
```

> [!NOTE]
> Agent 经 `BACKEND_AGENT_PORT` 以 HTTP 调用 `/api/internal/*`（私网/VPN IP）。Traefik 在 `:443` 上拦截这些路由。见 [Agent 网络与安全](docs/agent-network.zh-CN.md)。

## 前置条件

- Docker 与 Docker Compose

## 部署

1. 带子模块克隆：

```bash
git clone --recursive git@github.com:zeroDtree/server-manager.git
# 或普通 clone 后：
# git submodule update --init --recursive
```

2. 配置 `.env` 并部署（`deploy-prod.sh` 内部会运行 preflight 与 `secret.sh`）：

```ini
# .env — 部署前编辑
GSAD_PUBLIC_HOST=gsad.example.com
ACME_EMAIL=admin@example.com
```

```bash
cp .env.example .env
# 在 .env 中设置 GSAD_PUBLIC_HOST 与 ACME_EMAIL
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh
```

若未设置 `ADMIN_EMAIL`，部署后创建管理员：`ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh`。

本地 HTTP 栈（无 TLS）：在 `.env` 中设置 `GSAD_PUBLIC_HOST=localhost`，然后 `ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local`（见 [docs/local-prod.zh-CN.md](docs/local-prod.zh-CN.md)）。

3. 将 `GSAD_PUBLIC_HOST` 的 DNS 指向本机；开放 80、443 端口。Traefik 终结 HTTPS（Let's Encrypt）。
4. `deploy-prod.sh` 结束前会等待 backend 健康。
5. 使用步骤 2 的管理员登录。
6. **Admin → Import servers**（CSV）；[派生 agent PSK](docs/agent-psk.zh-CN.md)；在各 GPU 主机部署 [server-agent](server-agent/)。
7. **Admin → Import users**。

> [!WARNING]
> 将 `BACKEND_AGENT_PORT`（默认 `:8080`）限制为 GPU 主机 / VPN 网段 — 见 [docs/agent-network.zh-CN.md](docs/agent-network.zh-CN.md)。启用[备份](docs/backup.zh-CN.md)并定期测试恢复。

## 升级

```bash
git pull && git submodule update --init --recursive && \
  ./utils/deploy-prod.sh --no-admin
```

升级 GPU 主机 agent：`git pull && sudo ./deploy/install.sh`（[server-agent/README.md](server-agent/README.md)）。

## 配置

在 `.env` 中设置 `GSAD_PUBLIC_HOST` 与 `ACME_EMAIL`。`deploy-prod.sh` 会运行 [`secret.sh`](utils/secret.sh) 生成 `.env.secrets`。见 [`.env.example`](.env.example) 与 [`.env.secrets.example`](.env.secrets.example)。

## 其他环境

| 环境                             | 指南                                         |
| -------------------------------- | -------------------------------------------- |
| 开发（Vite + mock agents）       | [docs/dev.zh-CN.md](docs/dev.zh-CN.md)       |
| 本地栈（无 TLS）                 | [docs/local-prod.zh-CN.md](docs/local-prod.zh-CN.md) |

## 延伸阅读

- [docs/agent-network.zh-CN.md](docs/agent-network.zh-CN.md) — agent HTTP 访问与防火墙
- [docs/agent-psk.zh-CN.md](docs/agent-psk.zh-CN.md) — 每台 GPU 主机 PSK 派生
- [docs/backup.zh-CN.md](docs/backup.zh-CN.md) — 备份、恢复与日志轮转
- [account_prepare/README.md](account_prepare/README.md) — 表格 onboarding 流程
- [gsad-backend/README.md](gsad-backend/README.md) — API、schema、Flyway
- [server-agent/README.md](server-agent/README.md) — GPU 主机 agent 安装

License: [LICENSE](LICENSE)
