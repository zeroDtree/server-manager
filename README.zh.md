# GSAD — GPU 服务器访问控制台

[English](README.md) | 中文

GSAD 通过 Web 控制台管理 GPU 服务器的 SSH 访问。成员**申请访问**，后端 Agent 在 GPU 主机上**开通 Linux 账号**，轻量上报进程把 **GPU 指标**发回看板。中心主机用 Docker 运行整套服务，每台 GPU 机器部署 Agent。

文档：https://zerodtree.github.io/server-manager/zh/

```mermaid
flowchart TB
  Browser(["用户 / 浏览器"])

  subgraph central ["中心主机 (Docker)"]
    Traefik["Traefik :443"]
    UI["Vue UI"]
    Backend["Backend (Spring Boot)"]
    Traefik --> UI
    Traefik -->|"HTTPS /api JWT"| Backend
  end

  subgraph data ["数据层"]
    PG[("PostgreSQL")]
    RD[("Redis")]
  end

  subgraph agents ["GPU 主机 (Agents)"]
    Prov["account-provisioner"]
    Rep["gpu-server-report"]
  end

  Browser -->|"HTTPS :443"| Traefik
  Backend --> PG
  Backend --> RD
  Prov -->|"HTTP BACKEND_AGENT_PORT  /api/internal"| Backend
  Rep -->|"HTTP BACKEND_AGENT_PORT  /api/internal"| Backend
```

## 前置条件

- Docker 和 Docker Compose
- **生产 HTTPS：** 公网 IP，`GSAD_PUBLIC_HOST` 的 DNS A/AAAA，入站 TCP **80** 和 **443**（Traefik 经 Let's Encrypt 终止 TLS）

## 部署

1. 带 submodule 克隆：
    ```bash
    git clone --recursive git@github.com:zeroDtree/server-manager.git
    ```
2. 将 [`.env.example`](.env.example) 复制为 `.env`。
    ```bash
    cp .env.example .env
    ```
    编辑 `GSAD_PUBLIC_HOST`、`ACME_EMAIL` 和 `BACKEND_AGENT_BIND`。
3. 部署：
    ```
    ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh
    ```
4. 使用第 3 步的管理员邮箱（`ADMIN_EMAIL`）登录。
5. **管理 → 服务器管理** — 添加主机或导入 CSV（`server_id`、`agent_psk`）；见 [Agent PSK](docs/zh/agent-psk.md)。
6. 在每台 GPU 主机上部署 [server-agent](https://github.com/zeroDtree/server-agent)，使 `AGENT_SERVER_ID`=`server_id`、`AGENT_PSK`=`agent_psk`。
7. **管理 → 用户管理** — 导入用户。

## 升级

升级 Frontend 和 Backend：
```bash
git pull && git submodule update --init --recursive && \
  ./utils/deploy-prod.sh --no-admin
```

升级各 GPU 主机上的 Agent — 见 [server-agent](https://github.com/zeroDtree/server-agent)。

## 停止

停止栈（只停容器，保留数据卷）：

```bash
./utils/gsad-compose.sh down
```

## 部署模式

以上步骤使用默认 **prod** 栈：自带 Traefik，占用 80/443，Let's Encrypt 签发证书。
首次部署可加标志选择其他栈；之后升级会沿用 `.gsad-compose-mode` 中保存的模式。

- `--external` — 复用已有边缘 Traefik。见 [接入已有边缘 Traefik](docs/zh/external-traefik.md)。
- `--local` — 在 localhost 上用 HTTP 做类生产试用。与同机边缘 Traefik 冲突。见 [本地无 TLS 试用](docs/zh/local-prod.md)。

用 `--prod`、`--external` 或 `--local` 覆盖已保存的模式。

## 开发

本地 UI 加 mock GPU 主机（无 Traefik）：

```bash
./utils/dev-up.sh -d
cd gsad-frontend && npm install && npm run dev
```

打开 `http://localhost:5173`。预置管理员：`admin@gsad.local` / `Admin@123456`。见 [开发环境](docs/zh/dev.md)。

## 文档

- [用户手册](docs/zh/gsad-user-manual.md)
- [管理员手册](docs/zh/gsad-admin-manual.md)
- [本地无 TLS 试用](docs/zh/local-prod.md)
- [开发环境](docs/zh/dev.md)
- [Agent 网络与安全](docs/zh/agent-network.md)
- [接入已有边缘 Traefik](docs/zh/external-traefik.md)
- [Agent PSK](docs/zh/agent-psk.md)
- [备份与恢复](docs/zh/backup.md)
- [GPU 主机 Agent 安装](https://github.com/zeroDtree/server-agent)
- [学生注册开通流程（WPS → CSV → NetBird/GSAD → 邮件）](https://github.com/zeroDtree/account-prepare)
