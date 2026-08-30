# GSAD — GPU Server Access Dashboard

GSAD lets you manage SSH access to GPU servers through a web UI. Team members **apply for access**, backend agents **provision Linux accounts** on GPU hosts, and lightweight reporters **send GPU metrics** back to the dashboard. Everything runs in Docker on a single central host, with agents deployed on each GPU machine.

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
    PG[("PostgreSQL")]
    RD[("Redis")]
  end

  subgraph agents ["GPU Hosts (Agents)"]
    Prov["account-provisioner"]
    Rep["gpu-server-report"]
  end

  Browser -->|"HTTPS :443"| Traefik
  Backend --> PG
  Backend --> RD
  Prov -->|"HTTP BACKEND_AGENT_PORT  /api/internal"| Backend
  Rep -->|"HTTP BACKEND_AGENT_PORT  /api/internal"| Backend
```

## Prerequisites

- Docker and Docker Compose
- **Production HTTPS:** a public IP, DNS A/AAAA for `GSAD_PUBLIC_HOST`, inbound TCP **80** and **443** (Traefik terminates TLS via Let's Encrypt)

## Deploy

1. Clone with submodules:
    ```bash
    git clone --recursive git@github.com:zeroDtree/server-manager.git
    ```
2. Copy [`.env.example`](.env.example) to `.env`. 
    ```bash
    cp .env.example .env
    ```
    Edit `GSAD_PUBLIC_HOST`, `ACME_EMAIL`, and `BACKEND_AGENT_BIND`. 
3. Deploy the stack:
    ```
    ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh
    ```
4. Log in with the admin from step 2.
5. **Admin → Server management** — add hosts or import CSV (`server_id`, `agent_psk`); see [agent PSK](docs/agent-psk.md).
6. Deploy [server-agent](server-agent/) on each GPU host with the same `AGENT_SERVER_ID`=`server_id`, `AGENT_PSK`=`agent_psk`.
7. **Admin → User management** — import users.

## Upgrade

Upgrade Frontend and Backend:
```bash
git pull && git submodule update --init --recursive && \
  ./utils/deploy-prod.sh --no-admin
```

Upgrade Agents on each GPU host — see [server-agent/README.md](server-agent/README.md).

## Stop

Stop the stack (containers only; data volumes kept):

```bash
./utils/gsad-compose.sh down
```

## Deploy modes

The steps above use the default **prod** stack: bundled Traefik on 80/443 with Let's Encrypt.
Pass a flag on the first deploy for a different stack; later upgrades reuse the mode stored in `.gsad-compose-mode`.

- `--external` — reuse an existing edge Traefik. See [external Traefik](docs/external-traefik.md).
- `--local` — HTTP on localhost for a prod-like tryout. Conflicts with an edge Traefik on the same host. See [local prod](docs/local-prod.md).

Override a stored mode with `--prod`, `--external`, or `--local`.

## Docs

- [Local tryout without TLS](docs/local-prod.md)
- [UI & agent development setup](docs/dev.md)
- [Agent HTTP access and firewall rules](docs/agent-network.md)
- [Reuse an existing edge Traefik](docs/external-traefik.md)
- [Per-GPU host stored PSK](docs/agent-psk.md)
- [Backup, restore, and log rotation](docs/backup.md)
- [GPU host agent install](server-agent/README.md)
- [Student registration provisioning (WPS → CSV → NetBird/GSAD → email)](account_prepare/README.md)

License: [LICENSE](LICENSE)
