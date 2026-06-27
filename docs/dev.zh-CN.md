# 开发

**Languages:** [English](dev.md) · [简体中文](dev.zh-CN.md)

## 快速开始

```bash
./utils/dev-up.sh -d
cd gsad-frontend && npm install && npm run dev
```

`dev-up.sh` 会在缺失时创建 `.env` / `.env.secrets`、运行 `secret.sh` 并启动 mock profile 栈。`compose.override.yaml` 会自动合并 [`dockers/compose.dev.yaml`](../dockers/compose.dev.yaml) — backend、Postgres、Redis 绑定到主机。`mock` profile 启动两个开发 agent 容器（`account-provision-mock`、`gpu-server-report-mock`），各模拟最多 **100** 台服务器（`MOCK_SERVER_COUNT` 见 [`dockers/compose.yaml`](../dockers/compose.yaml)）。

| URL                                   | 用途                          |
| ------------------------------------- | ----------------------------- |
| http://localhost:5173                 | Vue UI（Vite 开发服务器）     |
| http://localhost:8080/api/*           | Backend API                   |
| http://localhost:8080/swagger-ui.html | Swagger UI（仅 dev profile）  |
| http://localhost:8080/v3/api-docs     | OpenAPI JSON（实时）          |

Vite 将 `/api` 代理到 `http://localhost:8080`（[`gsad-frontend/vite.config.ts`](../gsad-frontend/vite.config.ts)）。

## 种子数据

Flyway `dev` profile：管理员 `admin@gsad.local` / `Admin@123456`；mock 服务器 `gpu-mock-001` … `gpu-mock-100`。迁移变更后：

```bash
./utils/gsad-compose.sh --dev down -v
./utils/dev-up.sh -d
```
