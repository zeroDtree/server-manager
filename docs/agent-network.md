# Agent network and security

## Two entry paths

| Path            | Audience                  | Protocol | Routes                                                 |
| --------------- | ------------------------- | -------- | ------------------------------------------------------ |
| Users / browser | HTTPS `:443` via Traefik  | HTTPS    | `/`, `/api/*` (JWT)                                    |
| GPU agents      | Host `BACKEND_AGENT_PORT` | HTTP     | `/api/internal/*` (`X-Agent-Server-Id`, `X-Agent-PSK`) |

## Why HTTP, not the public HTTPS URL?

- Traefik blocks `/api/internal/*` on `:443` (by design).
- Agents use the central host's private/VPN IP (e.g. NetBird), not `https://${GSAD_PUBLIC_HOST}`.
- Avoids per-host TLS cert management; auth is the per-server PSK stored in GSAD (`X-Agent-Server-Id`, `X-Agent-PSK`).

## Network requirements

- Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts only — VPN mesh CIDR, private LAN, or firewall allowlist.
- Set `BACKEND_AGENT_BIND` to an address agents can reach on the central host.
- Prod startup allows **loopback**, **RFC1918** (`10/8`, `172.16–31/12`, `192.168/16`), or an IP in **`BACKEND_AGENT_VPN_CIDRS`** (comma-separated CIDRs). Rejects `0.0.0.0` and public IPs.

Example (NetBird overlay `100.67.0.0/16` — replace with your central host VPN IP):

```ini
BACKEND_AGENT_BIND=100.67.0.10
BACKEND_AGENT_VPN_CIDRS=100.67.0.0/16
```

> [!WARNING]
> Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts / VPN CIDR only. Exposing the agent port to the public internet is a security risk. See [docs/agent-network.md](docs/agent-network.md).


> [!WARNING]
> Do not expose `:8080` to the public internet. HTTP carries agent credentials in cleartext.

> [!IMPORTANT]
> Set a unique `AGENT_PSK` per GPU host in **Admin → Server management** (or the import CSV). Put that value only on the matching agent. See [Agent PSK (per GPU host)](agent-psk.md).

**Agent config:** `REPORT_API_URL=http://<central-vpn-or-private-ip>:8080`

Central host already running edge Traefik (NetBird, etc.)? Use [External edge Traefik](external-traefik.md) instead of GSAD bundled Traefik.
