# Agent network and security

## Overview

| Path            | Audience                  | Protocol | Routes                                                 |
| --------------- | ------------------------- | -------- | ------------------------------------------------------ |
| Users / browser | HTTPS `:443` via Traefik  | HTTPS    | `/`, `/api/*` (JWT)                                    |
| GPU agents      | Host `BACKEND_AGENT_PORT` | HTTP     | `/api/internal/*` (`X-Agent-Server-Id`, `X-Agent-PSK`) |

- Traefik blocks `/api/internal/*` on `:443` (by design).
- Agents use the central host's private/VPN IP, not `https://${GSAD_PUBLIC_HOST}`.
- Avoids per-host TLS cert management; auth is the per-server PSK stored in GSAD (`X-Agent-Server-Id`, `X-Agent-PSK`).

## Network requirements

- Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts only — VPN mesh CIDR, private LAN, or firewall allowlist.
- Set `BACKEND_AGENT_BIND` to an address agents can reach on the central host.
- Prod startup allows **loopback**, **RFC1918** (`10/8`, `172.16–31/12`, `192.168/16`), or an IP in **`BACKEND_AGENT_VPN_CIDRS`** (comma-separated CIDRs). Rejects `0.0.0.0` and public IPs.


> [!WARNING]
> Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts / VPN CIDR only. Exposing the agent port to the public internet is a security risk.
> Do not expose `:8080` to the public internet. HTTP carries agent credentials in cleartext.

Central host already running edge Traefik? Use [External edge Traefik](external-traefik.md) instead of GSAD bundled Traefik.
