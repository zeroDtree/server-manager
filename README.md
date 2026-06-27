# GSAD — GPU Server Access Dashboard

<p align="left">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

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

| [🚀 Production Deploy](#deploy) | [💻 Local Tryout (No TLS)](docs/local-prod.md) | [🛠️ UI & Agent Dev](docs/dev.md) | [👥 Student Onboarding](#account-preparation-spreadsheet--gsad--netbird) |
| :---: | :---: | :---: | :---: |

---

<details>
<summary><b>Table of contents</b> (click to expand)</summary>

- [GSAD — GPU Server Access Dashboard](#gsad--gpu-server-access-dashboard)
  - [Quick Links](#quick-links)
  - [Prerequisites](#prerequisites)
  - [Deploy](#deploy)
  - [Agent access \& security](#agent-access--security)
  - [After deploy](#after-deploy)
    - [First admin](#first-admin)
    - [Account preparation (spreadsheet → GSAD + NetBird)](#account-preparation-spreadsheet--gsad--netbird)
    - [Agent PSK (per GPU host)](#agent-psk-per-gpu-host)
    - [Backup and restore](#backup-and-restore)
    - [Upgrades and health](#upgrades-and-health)
  - [Repository layout](#repository-layout)
  - [Configuration](#configuration)
  - [Other setups](#other-setups)
  - [Tests](#tests)
  - [Further reading](#further-reading)

</details>

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
> Agents call `/api/internal/*` over HTTP on `BACKEND_AGENT_PORT` (private/VPN IP). Traefik blocks these routes on `:443`. See [Agent access & security](#agent-access--security).

## Prerequisites

- Docker and Docker Compose

## Deploy

1. Clone with submodules:

```bash
git clone --recursive git@github.com:zeroDtree/server-manager.git
# or, after a plain clone:
# git submodule update --init --recursive
```

2. Configure `.env` and deploy (`deploy-prod.sh` runs preflight and `secret.sh` internally):

```ini
# .env — edit before deploy
GSAD_PUBLIC_HOST=gsad.example.com
ACME_EMAIL=admin@example.com
```

```bash
cp .env.example .env
# edit GSAD_PUBLIC_HOST and ACME_EMAIL in .env
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh
```

Or deploy first, then create the admin: `ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh`.

Local HTTP stack (no TLS): set `GSAD_PUBLIC_HOST=localhost` in `.env`, then `ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local` (see [docs/local-prod.md](docs/local-prod.md)).

3. Point DNS for `GSAD_PUBLIC_HOST` at this host; open ports 80 and 443. Traefik terminates HTTPS (Let's Encrypt).
4. Backend health is verified by `deploy-prod.sh` (container healthcheck). To inspect manually:

```bash
./utils/gsad-compose.sh exec -T backend curl -sS http://localhost:8080/actuator/health
```

```json
{"status":"UP"}
```

5. Log in with the admin from step 2 (or [create one](#first-admin) if you skipped `ADMIN_EMAIL`).
6. **Admin → Import servers** (CSV); [derive agent PSKs](docs/agent-psk.md); deploy [server-agent](server-agent/) on each GPU host.
7. **Admin → Import users**.

> [!WARNING]
> **Network security (steps 8–9)**
> - Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts / VPN CIDR only — never expose it to the public internet.
> - HTTP carries agent credentials in cleartext; verify perimeter firewalls before enabling agents.
> - Enable [backups](docs/backup.md) and test restore periodically.

## Agent access & security

**Two entry paths**

| Path            | Audience                  | Protocol | Routes                                                 |
| --------------- | ------------------------- | -------- | ------------------------------------------------------ |
| Users / browser | HTTPS `:443` via Traefik  | HTTPS    | `/`, `/api/*` (JWT)                                    |
| GPU agents      | Host `BACKEND_AGENT_PORT` | HTTP     | `/api/internal/*` (`X-Agent-Server-Id`, `X-Agent-PSK`) |

**Why HTTP, not the public HTTPS URL?**

- Traefik blocks `/api/internal/*` on `:443` (by design).
- Agents use the central host's private/VPN IP (e.g. NetBird), not `https://${GSAD_PUBLIC_HOST}`.
- Avoids per-host TLS cert management; auth is per-server HMAC derived from `AGENT_MASTER_SECRET`.

**Network requirements**

- Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts only — NetBird mesh CIDR, private LAN, or firewall allowlist.
- Set `BACKEND_AGENT_BIND` to `127.0.0.1` or an RFC1918 address; startup rejects `0.0.0.0` and public IPs.

> [!WARNING]
> Do not expose `:8080` to the public internet. HTTP carries agent credentials in cleartext.

> [!IMPORTANT]
> Use a long random `AGENT_MASTER_SECRET` on the **backend only**; the backend rejects the default value. Per GPU host, derive `AGENT_PSK` — see [Agent PSK (per GPU host)](docs/agent-psk.md). Never put `AGENT_MASTER_SECRET` on GPU hosts.

**Agent config:** `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` — see [server-agent/README.md](server-agent/README.md).

## After deploy

### First admin

Flyway is schema-only; there is **no seeded admin** in production. **Set `ADMIN_EMAIL` on deploy** (step 2), or run [`create-prod-admin.sh`](utils/create-prod-admin.sh) immediately after the stack is healthy.

From the repo root:

```bash
ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh
```

Or set the password inline (do **not** store bootstrap passwords in `.env`):

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='your-strong-password' ./utils/create-prod-admin.sh
```

The script is **idempotent**: if an admin already exists, it exits without changes. For a clean bootstrap after dev/mock, run [`down -v`](docs/local-prod.md#reset-clean-db) on the [local HTTP stack](docs/local-prod.md), then `up` and this script again.

Optional env: `ADMIN_LINUX_USERNAME` (default `gsadadmin`), `ADMIN_DISPLAY_NAME` (default `Admin`).

Verify login:

```bash
curl -sS -X POST "https://${GSAD_PUBLIC_HOST}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<your-password>"}'
```

On the [local HTTP stack](docs/local-prod.md), use `http://localhost/api/auth/login` instead.

Change the bootstrap password via **Account → Change password** in the sidebar (or `POST /api/auth/change-password`).

Import users via **Admin → Import users**. Required columns: `email`, `linux_username`, `initial_password` (min 8 chars). Optional: `display_name`, `student_id`, `cohort`, `roles`. Distribute initial passwords out-of-band — they are never returned in the API response. Admins can reset a user's login password from **Admin → Users** (non-admin accounts only).

### Account preparation (spreadsheet → GSAD + NetBird)

Bulk onboarding from a registration spreadsheet is handled by [`account_prepare/`](account_prepare/): SQLite ledger, import CSVs under `data/account_prepare/`, NetBird/GSAD reconcile, and unified credential email. See [docs/info.md](docs/info.md) for what to collect from students and [account_prepare/README.md](account_prepare/README.md) for the full workflow (`prepare-accounts` → NetBird import → GSAD UI import → `reconcile-accounts` → `notify-accounts`).

### Agent PSK (per GPU host)

Each GPU agent uses a per-server HMAC derived from the backend-only `AGENT_MASTER_SECRET`. Derive `AGENT_PSK` on a trusted machine and deploy to agents — see [docs/agent-psk.md](docs/agent-psk.md).

### Backup and restore

Scheduled Postgres backups, log rotation, and restore — see [docs/backup.md](docs/backup.md).

### Upgrades and health

- Backend health: `/actuator/health`
- Agent health: `:9091` (provisioner), `:9092` (reporter)

```bash
curl -sS "https://${GSAD_PUBLIC_HOST}/actuator/health"
```

```json
{"status":"UP"}
```

Upgrade central stack:

```bash
git pull && git submodule update --init --recursive && \
  ./utils/deploy-prod.sh --no-admin
```

Upgrade agents on GPU hosts: `git pull && sudo ./deploy/install.sh`.

Pre-flight: use the [local HTTP stack](docs/local-prod.md) to validate images and routing before real DNS and TLS.

## Repository layout

Git submodules — run `git submodule update --init --recursive` after clone.

```text
server-manager/
├── gsad-backend/       # Spring Boot REST API
├── gsad-frontend/      # Vue 3 + Vite UI
├── server-agent/       # account-provisioner + gpu-server-report (systemd)
├── account_prepare/    # Spreadsheet onboarding (SQLite ledger)
├── netbird-manage/     # NetBird CLI (submodule)
├── dockers/            # Compose, Dockerfiles, mock agents
└── utils/              # Ops scripts (deploy-prod, gsad-compose, dev-up, secrets, admin, PSK, backup)
```

## Configuration

Deploy requires `GSAD_PUBLIC_HOST` and `ACME_EMAIL` in `.env`. Run [`secret.sh`](utils/secret.sh) to generate `.env.secrets` with random values ($\ge 32$ chars). Keys you have already set are not overwritten. Config comments in [`.env.example`](.env.example); secret keys in [`.env.secrets.example`](.env.secrets.example).

| Variable                         | File            | Required?    | Default     | Description                                                              |
| -------------------------------- | --------------- | ------------ | ----------- | ------------------------------------------------------------------------ |
| `GSAD_PUBLIC_HOST`               | `.env`          | **Required** | —           | Traefik hostname and DNS entry                                           |
| `ACME_EMAIL`                     | `.env`          | **Required** | —           | Let's Encrypt account email for TLS certificates                         |
| `SPRING_PROFILES_ACTIVE`         | `.env`          | **Required** | `dev`       | Set `prod` with `compose.prod.yaml`                                      |
| `CREDENTIALS_ENCRYPTION_KEY`     | `.env.secrets`  | **Required** | —           | AES key for SSH credentials at rest ($\ge 32$ chars)                     |
| `AGENT_MASTER_SECRET`            | `.env.secrets`  | **Required** | —           | Backend-only root; derive PSK via [docs/agent-psk.md](docs/agent-psk.md) |
| `JWT_SECRET`                     | `.env.secrets`  | **Required** | —           | JWT signing key ($\ge 32$ chars)                                         |
| `DB_PASSWORD` / `REDIS_PASSWORD` | `.env.secrets`  | **Required** | —           | Data store passwords                                                     |
| `BACKEND_AGENT_PORT`             | `.env`          | Optional     | `8080`      | Private host port for agent internal API                                 |
| `BACKEND_AGENT_BIND`             | `.env`          | Optional     | `127.0.0.1` | Loopback or RFC1918 internal IP only                                     |
| `CORS_ALLOWED_ORIGINS`           | `.env`          | Optional     | empty       | Usually empty when UI and API share host via Traefik                     |

> [!WARNING]
> Do not use placeholder values from `.env.secrets.example`. Run [`secret.sh`](utils/secret.sh) or set strong random values manually. Swagger is disabled in production; agent auth uses derived PSK + `X-Agent-Server-Id` over HTTP on the private port.

## Other setups

| Setup                            | Guide                                    |
| -------------------------------- | ---------------------------------------- |
| Development (Vite + mock agents) | [docs/dev.md](docs/dev.md)               |
| Local stack without TLS          | [docs/local-prod.md](docs/local-prod.md) |

## Tests

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```

License: [LICENSE](LICENSE)

## Further reading

- [docs/agent-psk.md](docs/agent-psk.md) — per-GPU host PSK derivation
- [docs/backup.md](docs/backup.md) — backup, restore, and log rotation
- [account_prepare/README.md](account_prepare/README.md) — spreadsheet onboarding workflow
- [gsad-backend/README.md](gsad-backend/README.md) — API routes, schema, Flyway
- [server-agent/README.md](server-agent/README.md) — GPU host agent install
- [gsad-frontend/openapi/openapi.json](gsad-frontend/openapi/openapi.json) — OpenAPI spec (checked in)
