# 本地类生产栈（仅 HTTP）

**Languages:** [English](local-prod.md) · [简体中文](local-prod.zh-CN.md)

在 localhost 上运行生产 compose 文件但不启用 TLS — 适用于在真实 DNS 与 Let's Encrypt 之前验证镜像与路由。

## 启动

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod up -d --build
```

打开 `http://localhost/`（UI）与 `http://localhost/api/*`（公开 API）。

`backend` 与 `postgres` 健康后，创建首个管理员 — 见主 README 的 [First admin](../README.zh-CN.md#first-admin)。

## Reset（清空数据库）

从 dev/mock 切换或重新测试 bootstrap 时使用。须与启动时**相同**的 `-f` 与 `--profile prod`，否则 Compose 可能指向错误 project/volume：

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod down -v
```

再拉起栈：

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod up -d --build
```

**`down -v` 会删除 `postgres_data`**（及本 project 其他 named volume）。dev 种子管理员（`admin@gsad.local`）与 mock 服务器一并清除。
