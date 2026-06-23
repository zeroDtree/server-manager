- [GSAD — GPU Server Access Dashboarda](#gsad--gpu-server-access-dashboarda)
  - [Prerequisites](#prerequisites)
  - [Quick start (dev)](#quick-start-dev)
  - [Architecture](#architecture)
  - [Repository layout](#repository-layout)
  - [Production](#production)
    - [Agent access \& security](#agent-access--security)
    - [Local prod-like stack (HTTP only)](#local-prod-like-stack-http-only)
    - [First admin (prod bootstrap)](#first-admin-prod-bootstrap)
    - [Backup schedule](#backup-schedule)
    - [Production checklist \& best practices](#production-checklist--best-practices)
  - [Configuration](#configuration)
  - [Tests](#tests)
  - [Further reading](#further-reading)


# GSAD — GPU Server Access Dashboarda

GPU server access management: users apply for SSH access; agents on GPU hosts provision accounts and report metrics. Stack: Spring Boot 4 / Java 21, Vue 3 + Vite, PostgreSQL 16, Redis 7, Traefik v3.

## Prerequisites

- Docker and Docker Compose
- Node.js (frontend dev only)
- Clone with submodules:

```bash
git clone --recursive git@github.com:zeroDtree/server-manager.git
# or, after a plain clone:
git submodule update --init --recursive
```

## Quick start (dev)

```bash
cp dockers/.env.example .env
docker compose --profile mock up --build
cd gsad-frontend && npm install && npm run dev
```

`compose.override.yaml` merges [`dockers/compose.dev.yaml`](dockers/compose.dev.yaml) automatically — backend, Postgres, and Redis bind to the host. The `mock` profile starts two dev agent containers (`account-provision-mock`, `gpu-server-report-mock`) that simulate up to **100** servers each (`MOCK_SERVER_COUNT` in [`dockers/compose.yaml`](dockers/compose.yaml)).

| URL                                   | Purpose                       |
| ------------------------------------- | ----------------------------- |
| http://localhost:5173                 | Vue UI (Vite dev server)      |
| http://localhost:8080/api/*           | Backend API                   |
| http://localhost:8080/swagger-ui.html | Swagger UI (dev profile only) |
| http://localhost:8080/v3/api-docs     | OpenAPI JSON (live)           |

Vite proxies `/api` to `http://localhost:8080` ([`gsad-frontend/vite.config.ts`](gsad-frontend/vite.config.ts)).

**Dev seed data** (Flyway `dev` profile): admin `admin@gsad.local` / `Admin@123456`; mock servers `gpu-mock-001` … `gpu-mock-100`. After migration changes: `docker compose down -v`, then re-up.

## Architecture

```mermaid
flowchart LR
  subgraph dev [Dev]
    UI[Vite_UI_5173]
    API[Backend_8080]
    UI -->|"/api proxy"| API
  end
  subgraph data [Data]
    PG[(PostgreSQL)]
    RD[(Redis)]
  end
  API --> PG
  API --> RD
  subgraph agents [GPU_hosts]
    Prov[account_provisioner]
    Rep[gpu_server_report]
  end
  Prov -->|"/api/internal"| API
  Rep -->|"/api/internal"| API
```

In production, traffic splits into two paths: users reach the UI and public `/api` over HTTPS via Traefik; GPU agents reach `/api/internal/*` over plain HTTP on `BACKEND_AGENT_PORT` (see [Agent access & security](#agent-access--security)).

## Repository layout

Git submodules — run `git submodule update --init --recursive` after clone.

| Path                            | Role                                                               |
| ------------------------------- | ------------------------------------------------------------------ |
| [gsad-backend](gsad-backend/)   | REST API, Flyway, internal agent routes                            |
| [gsad-frontend](gsad-frontend/) | Vue UI                                                             |
| [server-agent](server-agent/)   | account-provisioner + gpu-server-report (systemd on GPU hosts)     |
| [dockers](dockers/)             | Compose files, Dockerfiles, and dev mock agents (`dockers/mocks/`) |
| [utils](utils/)                 | Repo-level ops scripts (DB backup, optional systemd units)         |

## Production

**Central stack** (one host, Traefik on `gsad_traefik` network):

```bash
cp dockers/.env.example .env
# Set SPRING_PROFILES_ACTIVE=prod, GSAD_PUBLIC_HOST, ACME_EMAIL, strong secrets
# DNS for GSAD_PUBLIC_HOST must point at this host; open ports 80 and 443
docker compose -f compose.yaml -f dockers/compose.prod.yaml --profile prod up -d --build
```

Traefik terminates HTTPS (Let's Encrypt). Agent access uses a separate HTTP port — details below.

### Agent access & security

**Two entry paths**

| Path            | Audience                         | Protocol            | Routes                            |
| --------------- | -------------------------------- | ------------------- | --------------------------------- |
| Users / browser | HTTPS `:443` via Traefik         | `/`, `/api/*` (JWT) |
| GPU agents      | Direct host `BACKEND_AGENT_PORT` | HTTP                | `/api/internal/*` (`X-Agent-PSK`) |

**Why HTTP, not the public HTTPS URL?**

- Traefik blocks `/api/internal/*` on `:443` (by design).
- Agents use the central host's private/VPN IP (e.g. NetBird), not `https://${GSAD_PUBLIC_HOST}`.
- Avoids per-host TLS cert management; auth is via shared `AGENT_PSK`.

**Network requirements (required in prod)**

- Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts only — NetBird mesh CIDR, private LAN, or firewall allowlist.
- Set `BACKEND_AGENT_BIND` to the central host's private/VPN IP (not `0.0.0.0` on internet-facing servers).
- Do not expose `:8080` to the public internet (HTTP carries `X-Agent-PSK` in cleartext).
- Use a long random `AGENT_PSK`; prod startup rejects the default value.

**Agent config:** `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` — see [server-agent/README.md](server-agent/README.md).

### Local prod-like stack (HTTP only)

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod up -d --build
```

Open `http://localhost/` (UI) and `http://localhost/api/*` (public API).

**Reset (clean DB)** — use when switching from dev/mock or re-testing bootstrap. Use the **same** `-f` files and `--profile prod` as start, or Compose may target the wrong project/volumes:

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod down -v
```

Then bring the stack back:

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod up -d --build
```

**`down -v` deletes `postgres_data`** (and other named volumes in this project). Dev seed admin (`admin@gsad.local`) and mock servers are removed.

**GPU hosts:** deploy [server-agent](server-agent/) on each machine — see [Agent access & security](#agent-access--security) and [server-agent/README.md](server-agent/README.md).

Prod Flyway is schema-only; servers register via the agent report API. There is **no seeded admin** in prod — create the first admin with [`create-prod-admin.sh`](gsad-backend/deploy/scripts/create-prod-admin.sh) after the stack is healthy (see [First admin](#first-admin-prod-bootstrap)).

### First admin (prod bootstrap)

After `backend` and `postgres` are healthy, from the repo root:

```bash
ADMIN_EMAIL=admin@example.com ./gsad-backend/deploy/scripts/create-prod-admin.sh
```

Or set the password inline (do **not** store bootstrap passwords in `.env`):

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='your-strong-password' ./gsad-backend/deploy/scripts/create-prod-admin.sh
```

The script is **idempotent**: if an admin already exists, it exits without changes. For a clean prod-local bootstrap after dev/mock, run [`down -v`](#local-prod-like-stack-http-only) first, then `up` and this script again.

Optional env: `ADMIN_LINUX_USERNAME` (default `gsadadmin`), `ADMIN_DISPLAY_NAME` (default `Admin`).

Verify login (prod-local):

```bash
curl -sS -X POST "http://localhost/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<your-password>"}'
```

Verify login (real prod over HTTPS):

```bash
curl -sS -X POST "https://${GSAD_PUBLIC_HOST}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"<your-password>"}'
```

Then import users via **Admin → Import CSV** (header: `email,linux_username,display_name,student_id,cohort,initial_password,roles`).

### Backup schedule

DB backup script: [`utils/backup-postgres.sh`](utils/backup-postgres.sh). Defaults: 30-day retention, 500 MB total cap under `<repo>/backups/`. Override with `BACKUP_DIR`, `RETENTION_DAYS`, `MAX_TOTAL_MB`.

Container logs are rotated at 10 MB × 3 files per service (see [`dockers/compose.yaml`](dockers/compose.yaml)). DB backups are capped as above.

**systemd timer** (recommended): installs units with `@REPO_ROOT@` resolved to this clone; output goes to journald:

```bash
sudo ./utils/install-backup-timer.sh
```

Check status: `systemctl status gsad-backup-postgres.timer` · View logs: `journalctl -t gsad-backup`

**Cron** (alternative; daily at 03:00; use your clone path):

```cron
0 3 * * * cd /opt/server-manager && ./utils/backup-postgres.sh 2>&1 | logger -t gsad-backup
```

After changing compose logging options, recreate containers so limits apply:

```bash
docker compose --profile prod up -d --force-recreate
docker inspect gsad-backend-1 --format '{{.HostConfig.LogConfig}}'
# expect: map[max-file:3 max-size:10m]
```

**Restore** (maintenance window — stop backend or pause writes first):

```bash
gunzip -c backups/gsad_YYYYMMDD_HHMMSS.sql.gz | docker compose exec -T postgres psql -U gsad gsad
```

### Production checklist & best practices

1. Generate strong random `JWT_SECRET` (≥32 chars), `AGENT_PSK`, `DB_PASSWORD`, `REDIS_PASSWORD`.
2. Point DNS for `GSAD_PUBLIC_HOST` at the host; open ports 80 and 443.
3. Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts / VPN CIDR only — never expose it on the public internet.
4. Start the prod stack; wait for `backend` health OK.
5. Run [`create-prod-admin.sh`](gsad-backend/deploy/scripts/create-prod-admin.sh); log in and change the bootstrap password.
6. Import users via Admin CSV import.
7. Deploy [server-agent](server-agent/) on each GPU host with a unique `AGENT_SERVER_ID`.
8. Enable backup cron or systemd timer; test a restore periodically.

**Security:** do not use placeholder secrets from [`dockers/.env.example`](dockers/.env.example); prod disables Swagger; agent auth uses `X-Agent-PSK` over HTTP on the private port.

**Operations:** backend health at `/actuator/health`; agent health at `:9091` (provisioner) and `:9092` (reporter). Upgrade central stack: `git pull && git submodule update --init --recursive && docker compose -f compose.yaml -f dockers/compose.prod.yaml --profile prod up -d --build`. Upgrade agents on GPU hosts: `git pull && sudo ./deploy/install.sh`.

**Pre-flight:** use [prod-local](#local-prod-like-stack-http-only) to validate images and routing before real DNS and TLS.

## Configuration

Copy `dockers/.env.example` to `.env` at the repo root.

| Variable                         | Description                                                                                         |
| -------------------------------- | --------------------------------------------------------------------------------------------------- |
| `SPRING_PROFILES_ACTIVE`         | `dev` (default) or `prod`                                                                           |
| `GSAD_PUBLIC_HOST`               | Public hostname for Traefik (prod); use `localhost` for prod-local                                  |
| `ACME_EMAIL`                     | Let's Encrypt email (prod HTTPS)                                                                    |
| `BACKEND_AGENT_PORT`             | Host port for GPU agent internal API (default `8080`)                                               |
| `BACKEND_AGENT_BIND`             | Required with prod compose: private/VPN IP (or `127.0.0.1` for prod-local)                          |
| `CREDENTIALS_ENCRYPTION_KEY`     | AES key for SSH credential columns at rest (≥32 chars; required in prod)                            |
| `AGENT_PSK`                      | `X-Agent-PSK` for internal APIs                                                                     |
| `JWT_SECRET`                     | JWT signing key (≥32 chars in prod)                                                                 |
| `DB_PASSWORD` / `REDIS_PASSWORD` | Data store passwords                                                                                |
| `CORS_ALLOWED_ORIGINS`           | Optional prod CORS origins (comma-separated); empty when UI and API share the same host via Traefik |

In `prod`, replace all placeholders in `.env` with strong random secrets; do not use values from `dockers/.env.example` as-is.

## Tests

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```

## Further reading

- [gsad-backend/README.md](gsad-backend/README.md) — API routes, schema, Flyway
- [server-agent/README.md](server-agent/README.md) — GPU host agent install
- [gsad-frontend/openapi/openapi.json](gsad-frontend/openapi/openapi.json) — OpenAPI spec (checked in)
