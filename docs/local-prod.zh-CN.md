# 本地类生产栈（仅 HTTP）

**Languages:** [English](local-prod.md) · [简体中文](local-prod.zh-CN.md)

在 localhost 上运行生产 compose 文件但不启用 TLS — 适用于在真实 DNS 与 Let's Encrypt 之前验证镜像与路由。

## 启动

在 `.env` 中设置 `GSAD_PUBLIC_HOST=localhost`，然后部署：

```bash
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local
```

打开 `http://localhost/`（UI）与 `http://localhost/api/*`（公开 API）。

`deploy-prod.sh` 会运行 preflight、生成 `.env.secrets`、等待 backend 健康，并在设置 `ADMIN_EMAIL` 时创建首个管理员。

## Reset（清空数据库）

从 dev/mock 切换或重新测试 bootstrap 时使用：

```bash
./utils/gsad-compose.sh --local down -v
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local
```

**`down -v` 会删除 `postgres_data`**（及本 project 其他 named volume）。dev 种子管理员（`admin@gsad.local`）与 mock 服务器一并清除。
