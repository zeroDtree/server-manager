# Agent 网络与安全

**Languages:** [English](agent-network.md) · [简体中文](agent-network.zh-CN.md)

## 两条入口

| 路径            | 受众                 | 协议  | 路由                                                   |
| --------------- | -------------------- | ----- | ------------------------------------------------------ |
| 用户 / 浏览器   | HTTPS `:443` Traefik | HTTPS | `/`、`/api/*`（JWT）                                   |
| GPU agent       | `BACKEND_AGENT_PORT` | HTTP  | `/api/internal/*`（`X-Agent-Server-Id`、`X-Agent-PSK`） |

## 为何用 HTTP 而非公网 HTTPS？

- Traefik 在 `:443` 上按设计拦截 `/api/internal/*`。
- Agent 使用中心主机私网/VPN IP（如 NetBird），而非 `https://${GSAD_PUBLIC_HOST}`。
- 避免每台主机管理 TLS 证书；认证为基于 `AGENT_MASTER_SECRET` 派生的 per-server HMAC。

## 网络要求

- 将 `BACKEND_AGENT_PORT`（默认 `:8080`）限制为仅 GPU 主机 — NetBird mesh CIDR、私网 LAN 或防火墙白名单。
- `BACKEND_AGENT_BIND` 设为 `127.0.0.1` 或 RFC1918 地址；启动时拒绝 `0.0.0.0` 与公网 IP。

> [!WARNING]
> 勿将 `:8080` 暴露到公网。HTTP 明文传输 agent 凭据。

> [!IMPORTANT]
> 在**仅 backend** 使用足够长的随机 `AGENT_MASTER_SECRET`；backend 拒绝默认值。每台 GPU 主机派生 `AGENT_PSK` — 见 [Agent PSK (per GPU host)](agent-psk.zh-CN.md)。切勿将 `AGENT_MASTER_SECRET` 部署到 GPU 主机。

**Agent 配置：** `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080`
