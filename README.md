# GSAD — GPU Server Access Dashboard

[![Java](https://img.shields.io/badge/Java-21-orange.svg)](https://www.oracle.com/java/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.0-green.svg)](https://spring.io/projects/spring-boot)
[![Vue](https://img.shields.io/badge/Vue-3.x-42b883.svg)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-Latest-646cff.svg)](https://vitejs.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg)](https://redis.io/)
[![Traefik](https://img.shields.io/badge/Traefik-v3-24A1C1.svg)](https://traefik.io/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)

> Self-hosted dashboard for GPU SSH access: users apply, agents provision accounts, and reporters send metrics.

## Quick Links

| [🚀 Production Deploy](#deploy) | [💻 Local Tryout (No TLS)](docs/local-prod.md) | [🛠️ UI & Agent Dev](docs/dev.md) | [👥 Student Onboarding](account_prepare/README.md) |
| :---: | :---: | :---: | :---: |

---

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
    PG[("PostgreSQL 16")]
    RD[("Redis 7")]
  end

  subgraph agents ["GPU Hosts (Agents)"]
    Prov["account-provisioner"]
    Rep["gpu-server-report"]
  end

  Browser -->|"HTTPS :443"| Traefik
  Backend --> PG
  Backend --> RD
  Prov -->|"HTTP BACKEND_AGENT_PORT /api/internal"| Backend
  Rep -->|"HTTP BACKEND_AGENT_PORT /api/internal"| Backend

  classDef central fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
  classDef data fill:#efebe9,stroke:#795548,stroke-width:2px
  classDef agents fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
  class Traefik,UI,Backend central
  class PG,RD data
  class Prov,Rep agents
```

> [!NOTE]
> Agents call `/api/internal/*` over HTTP on `BACKEND_AGENT_PORT` (private/VPN IP). Traefik blocks these routes on `:443`. See [Agent network and security](docs/agent-network.md).

## Prerequisites

- Docker and Docker Compose
- **Production HTTPS:** A server with a public IP reachable from the internet (this host, where you run the deploy steps below). Point DNS A/AAAA records for `GSAD_PUBLIC_HOST` at that address; allow inbound TCP **80** and **443** (Traefik terminates TLS and obtains Let's Encrypt certificates).

## Deploy

1. Clone with submodules:

```bash
git clone --recursive git@github.com:zeroDtree/server-manager.git
# or, after a plain clone:
# git submodule update --init --recursive
```

2. Configure `.env` and deploy (`deploy-prod.sh` runs preflight and `secret.sh` internally):

```bash
cp .env.example .env
```

```ini
# edit GSAD_PUBLIC_HOST and ACME_EMAIL in .env
GSAD_PUBLIC_HOST=gsad.example.com
ACME_EMAIL=admin@example.com
```

```bash
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh
```

If you skipped `ADMIN_EMAIL`, create the admin after deploy: `ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh`.

Local HTTP stack (no TLS): set `GSAD_PUBLIC_HOST=localhost` in `.env`, then `ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local` (see [docs/local-prod.md](docs/local-prod.md)).

3. Log in with the admin from step 2.
4. **Admin → Import servers** (CSV); [derive agent PSKs](docs/agent-psk.md); deploy [server-agent](server-agent/) on each GPU host.
5. **Admin → Import users**.

> [!WARNING]
> Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts / VPN CIDR only — see [docs/agent-network.md](docs/agent-network.md). Enable [backups](docs/backup.md) and test restore periodically.

## Upgrade

```bash
git pull && git submodule update --init --recursive && \
  ./utils/deploy-prod.sh --no-admin
```

Upgrade agents on GPU hosts ([server-agent/README.md](server-agent/README.md)):

```bash
# On each GPU host, inside the server-agent clone:
git pull && git submodule update --init --recursive && sudo ./deploy/install.sh
```

## Configuration

Set `GSAD_PUBLIC_HOST` and `ACME_EMAIL` in `.env`. `deploy-prod.sh` runs [`secret.sh`](utils/secret.sh) to generate `.env.secrets`. See [`.env.example`](.env.example) and [`.env.secrets.example`](.env.secrets.example).

## Other setups

| Setup                            | Guide                                    |
| -------------------------------- | ---------------------------------------- |
| Development (Vite + mock agents) | [docs/dev.md](docs/dev.md)               |
| Local stack without TLS          | [docs/local-prod.md](docs/local-prod.md) |

## Further reading

- [docs/agent-network.md](docs/agent-network.md) — agent HTTP access and firewall rules
- [docs/agent-psk.md](docs/agent-psk.md) — per-GPU host PSK derivation
- [docs/backup.md](docs/backup.md) — backup, restore, and log rotation
- [account_prepare/README.md](account_prepare/README.md) — spreadsheet onboarding workflow
- [gsad-backend/README.md](gsad-backend/README.md) — API routes, schema, Flyway
- [server-agent/README.md](server-agent/README.md) — GPU host agent install

License: [LICENSE](LICENSE)
