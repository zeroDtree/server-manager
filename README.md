# GSAD — GPU Server Access Dashboard

GPU server access management: users apply for SSH access; agents on GPU hosts provision accounts and report metrics. Stack: Spring Boot 4 / Java 21, Vue 3 + Vite, PostgreSQL 16, Redis 7, Traefik v3.

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

## Prerequisites

- Docker and Docker Compose
- Node.js (frontend dev only)
- Clone with submodules:

```bash
git clone --recursive git@github.com:zeroDtree/server-manager.git
# or, after a plain clone:
git submodule update --init --recursive
```

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

| Path            | Audience                         | Protocol            | Routes                                                 |
| --------------- | -------------------------------- | ------------------- | ------------------------------------------------------ |
| Users / browser | HTTPS `:443` via Traefik         | `/`, `/api/*` (JWT) |
| GPU agents      | Direct host `BACKEND_AGENT_PORT` | HTTP                | `/api/internal/*` (`X-Agent-Server-Id`, `X-Agent-PSK`) |

**Why HTTP, not the public HTTPS URL?**

- Traefik blocks `/api/internal/*` on `:443` (by design).
- Agents use the central host's private/VPN IP (e.g. NetBird), not `https://${GSAD_PUBLIC_HOST}`.
- Avoids per-host TLS cert management; auth is per-server HMAC derived from `AGENT_MASTER_SECRET`.

**Network requirements (required in prod)**

- Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts only — NetBird mesh CIDR, private LAN, or firewall allowlist.
- Set `BACKEND_AGENT_BIND` to the central host's private/VPN IP (prod rejects `0.0.0.0`).
- Do not expose `:8080` to the public internet (HTTP carries agent credentials in cleartext).
- Use a long random `AGENT_MASTER_SECRET` on the **backend only**; prod startup rejects the default value.
- Per GPU host: derive `AGENT_PSK` — see [Agent PSK (per GPU host)](#agent-psk-per-gpu-host). **Never** put `AGENT_MASTER_SECRET` on GPU hosts.

**Agent config:** `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` — see [server-agent/README.md](server-agent/README.md).

## Getting started

| Mode            | Guide                                      |
| --------------- | ------------------------------------------ |
| Development     | [docs/dev.md](docs/dev.md)                 |
| Local prod-like | [docs/local-prod.md](docs/local-prod.md)   |

## Production operations

Ongoing prod setup and ops after the stack is running (prod or prod-local).

### First admin (prod bootstrap)

Prod Flyway is schema-only; servers register via the agent report API. There is **no seeded admin** in prod — create the first admin with [`create-prod-admin.sh`](utils/create-prod-admin.sh) after the stack is healthy.

After `backend` and `postgres` are healthy, from the repo root:

```bash
ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh
```

Or set the password inline (do **not** store bootstrap passwords in `.env`):

```bash
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='your-strong-password' ./utils/create-prod-admin.sh
```

The script is **idempotent**: if an admin already exists, it exits without changes. For a clean prod-local bootstrap after dev/mock, run [`down -v`](docs/local-prod.md#reset-clean-db) first, then `up` and this script again.

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

Then import users via **Admin → Import CSV**. Required columns: `email`, `linux_username`, `initial_password` (min 8 chars). Optional: `display_name`, `student_id`, `cohort`, `roles`. Distribute initial passwords out-of-band — they are never returned in the API response.

### Agent PSK (per GPU host)

Each GPU agent authenticates with a per-server HMAC derived from the backend-only `AGENT_MASTER_SECRET`. Run [`derive-agent-psk.sh`](utils/derive-agent-psk.sh) on a trusted machine with a TTY (your laptop or the central host — **not** on GPU agents). The script prompts for the master secret twice; it is never read from env or argv.

From the repo root, after you know `AGENT_SERVER_ID` for that host:

```bash
./utils/derive-agent-psk.sh <AGENT_SERVER_ID>
```

Capture stdout for agent config (prints only the derived hex):

```bash
AGENT_PSK=$(./utils/derive-agent-psk.sh gpu-node-01)
```

Paste the hex into the agent's `AGENT_PSK` in [`server-agent/deploy/env/common.env`](server-agent/deploy/env/common.env). **Never** deploy `AGENT_MASTER_SECRET` to GPU hosts.

Set `REPORT_API_URL=http://<central-netbird-or-private-ip>:8080` on each agent — see [Agent access & security](#agent-access--security) and [server-agent/README.md](server-agent/README.md).

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

1. Generate strong random `JWT_SECRET` (≥32 chars), `AGENT_MASTER_SECRET`, `DB_PASSWORD`, `REDIS_PASSWORD`.
2. Point DNS for `GSAD_PUBLIC_HOST` at the host; open ports 80 and 443.
3. Restrict `BACKEND_AGENT_PORT` (default `:8080`) to GPU hosts / VPN CIDR only — never expose it on the public internet.
4. Start the prod stack; wait for `backend` health OK.
5. Run [`create-prod-admin.sh`](utils/create-prod-admin.sh); log in and change the bootstrap password.
6. Import users via Admin CSV import.
7. Deploy [server-agent](server-agent/) on each GPU host: register `AGENT_SERVER_ID`, then [derive `AGENT_PSK`](#agent-psk-per-gpu-host).
8. Enable backup cron or systemd timer; test a restore periodically.

**Security:** do not use placeholder secrets from [`dockers/.env.example`](dockers/.env.example); prod disables Swagger; agent auth uses derived PSK + `X-Agent-Server-Id` over HTTP on the private port.

**Operations:** backend health at `/actuator/health`; agent health at `:9091` (provisioner) and `:9092` (reporter). Upgrade central stack: `git pull && git submodule update --init --recursive && docker compose -f compose.yaml -f dockers/compose.prod.yaml --profile prod up -d --build`. Upgrade agents on GPU hosts: `git pull && sudo ./deploy/install.sh`.

**Pre-flight:** use [prod-local](docs/local-prod.md) to validate images and routing before real DNS and TLS.

## Repository layout

Git submodules — run `git submodule update --init --recursive` after clone.

| Path                            | Role                                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| [gsad-backend](gsad-backend/)   | REST API, Flyway, internal agent routes                                                                            |
| [gsad-frontend](gsad-frontend/) | Vue UI                                                                                                             |
| [server-agent](server-agent/)   | account-provisioner + gpu-server-report (systemd on GPU hosts)                                                     |
| [dockers](dockers/)             | Compose files, Dockerfiles, and dev mock agents (`dockers/mocks/`)                                                 |
| [utils](utils/)                 | Repo-level ops scripts (prod admin bootstrap, agent PSK derivation, server registration, DB backup, systemd units) |

## Configuration

Copy `dockers/.env.example` to `.env` at the repo root.

| Variable                         | Description                                                                                                                                    |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `SPRING_PROFILES_ACTIVE`         | `dev` (default) or `prod`                                                                                                                      |
| `GSAD_PUBLIC_HOST`               | Public hostname for Traefik (prod); use `localhost` for prod-local                                                                             |
| `ACME_EMAIL`                     | Let's Encrypt email (prod HTTPS)                                                                                                               |
| `BACKEND_AGENT_PORT`             | Host port for GPU agent internal API (default `8080`)                                                                                          |
| `BACKEND_AGENT_BIND`             | Required with prod compose: private/VPN IP (or `127.0.0.1` for prod-local)                                                                     |
| `CREDENTIALS_ENCRYPTION_KEY`     | AES key for SSH credential columns at rest (≥32 chars; required in prod)                                                                       |
| `AGENT_MASTER_SECRET`            | Backend-only master secret (≥32 chars); used to derive per-host `AGENT_PSK` via interactive `derive-agent-psk.sh` — never deploy to GPU agents |
| `JWT_SECRET`                     | JWT signing key (≥32 chars in prod)                                                                                                            |
| `DB_PASSWORD` / `REDIS_PASSWORD` | Data store passwords                                                                                                                           |
| `CORS_ALLOWED_ORIGINS`           | Optional prod CORS origins (comma-separated); empty when UI and API share the same host via Traefik                                            |

In `prod`, replace all placeholders in `.env` with strong random secrets; do not use values from `dockers/.env.example` as-is.

## Tests

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```

## Further reading

- [docs/dev.md](docs/dev.md) — local development with mock agents
- [docs/local-prod.md](docs/local-prod.md) — prod-like stack over HTTP on localhost
- [gsad-backend/README.md](gsad-backend/README.md) — API routes, schema, Flyway
- [server-agent/README.md](server-agent/README.md) — GPU host agent install
- [gsad-frontend/openapi/openapi.json](gsad-frontend/openapi/openapi.json) — OpenAPI spec (checked in)
