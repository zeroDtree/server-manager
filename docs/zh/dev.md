# 开发环境

用 mock GPU Agent 跑中心栈，Vue UI 走 Vite。

## 快速开始

```bash
./utils/dev-up.sh -d
cd gsad-frontend && npm install && npm run dev
```

打开 `http://localhost:5173`。Vite 开发服务器把 `/api` 代理到 `VITE_PROXY_TARGET`（默认 `http://localhost:8080`）。

预置管理员：`admin@gsad.local` / `Admin@123456`。

右上角 **语言** 可在 中文 / English 之间切换。拍中文手册截图时使用中文界面；拍英文手册截图时使用 English。

## Mock 栈提供什么

`./utils/dev-up.sh` 以 **dev** 模式启动 Docker Compose（`--profile mock`）：

- 后端（Spring `dev` profile）、PostgreSQL、Redis
- Flyway `dev` 种子数据：上述管理员；mock 服务器 `gpu-mock-001` … `gpu-mock-100`，共用 Agent PSK `dev-mock-agent-psk-0001`
- `account-provision-mock` — 对后端模拟授予 / 回收 Linux 风格访问
- `gpu-server-report-mock` — 上报假 GPU 指标，让资源看板有数据

迁移变更之后：

```bash
./utils/gsad-compose.sh --dev down -v
./utils/dev-up.sh -d
```

## 主机端口冲突

Dev Compose 会在主机上发布 Postgres **5432**、Redis **6379** 和后端 **8080**。若端口已被占用，可覆盖：

```bash
GSAD_DEV_POSTGRES_PORT=15432 \
GSAD_DEV_REDIS_PORT=16380 \
GSAD_DEV_BACKEND_PORT=18080 \
  ./utils/dev-up.sh -d

cd gsad-frontend && VITE_PROXY_TARGET=http://localhost:18080 npm run dev
```

## 预览本文档

```bash
cd docs && npm install && npm run dev
```

VitePress 在打印出的本地地址提供手册（截图在 `docs/assets/en/` 与 `docs/assets/zh/`）。站点根路径为英文，`/zh/` 为中文。

### 重拍截图

手册使用 1440×900（2×）的控制台 PNG。UI 在 `:5173` 且已安装 Playwright 时：

```bash
# 一次性：npm install playwright && npx playwright install chromium
PLAYWRIGHT_ROOT=/path/to/playwright-install \
  GSAD_DOCS_LOCALE=en \
  node docs/scripts/capture-screenshots.mjs

PLAYWRIGHT_ROOT=/path/to/playwright-install \
  GSAD_DOCS_LOCALE=zh \
  node docs/scripts/capture-screenshots.mjs
```

脚本写入 kebab-case 文件，例如 `board.png`、`application-detail.png`、`admin-users-import.png`。不要截操作系统文件选择器；应用内导入对话框即可。Agent PSK 保持遮盖。

## 测试

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```
