# Agent 网络与安全

## 概览

| 路径 | 对象 | 协议 | 路由 |
| --------------- | ------------------------- | -------- | ------------------------------------------------------ |
| 用户 / 浏览器 | 经 Traefik 的 HTTPS `:443` | HTTPS | `/`、`/api/*`（JWT） |
| GPU Agent | 主机 `BACKEND_AGENT_PORT` | HTTP | `/api/internal/*`（`X-Agent-Server-Id`、`X-Agent-PSK`） |

- Traefik 会在 `:443` 上拦截 `/api/internal/*`（有意为之）。
- Agent 使用中心主机的私网 / VPN IP，而不是 `https://${GSAD_PUBLIC_HOST}`。
- 避免为每台主机管理 TLS 证书；认证使用 GSAD 中按服务器存储的 PSK（`X-Agent-Server-Id`、`X-Agent-PSK`）。

## 网络要求

- 将 `BACKEND_AGENT_PORT`（默认 `:8080`）仅开放给 GPU 主机 —— VPN mesh CIDR、私有局域网或防火墙白名单。
- 将 `BACKEND_AGENT_BIND` 设为 Agent 能访问到的中心主机地址。
- 生产启动允许 **loopback**、**RFC1918**（`10/8`、`172.16–31/12`、`192.168/16`），或 **`BACKEND_AGENT_VPN_CIDRS`** 中的 IP（逗号分隔的 CIDR）。拒绝 `0.0.0.0` 和公网 IP。

> [!WARNING]
> 将 `BACKEND_AGENT_PORT`（默认 `:8080`）仅开放给 GPU 主机 / VPN CIDR。把 Agent 端口暴露到公网有安全风险。
> 不要把 `:8080` 暴露到公网。HTTP 会明文携带 Agent 凭证。

中心主机已经在跑边缘 Traefik？请改用 [接入已有边缘 Traefik](external-traefik.md)，而不是 GSAD 自带 Traefik。
