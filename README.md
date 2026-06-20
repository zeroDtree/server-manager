# GSAD (GPU Server Access Dashboard)

Full-stack GPU server access management: Spring Boot backend, Vue frontend, and GPU host agents.

## Quick start (dev)

```bash
cp dockers/.env.example .env
docker compose --profile mock up --build   # backend :8080, postgres, redis, mock agents
cd frontend && npm run dev                 # Vite → localhost:8080
```

Flyway **dev** seeds admin user + 30 mock servers (`gpu-mock-001` … `030`). After migration changes: `docker compose down -v` then re-up.

Public API: [frontend/openapi/openapi.json](frontend/openapi/openapi.json)

## Layout

| Path | Role |
|------|------|
| [backend/gsad](backend/gsad/) | REST API, Flyway, internal agent routes |
| [frontend](frontend/) | Vue UI |
| [server-agent](server-agent/) | account-provisioner + gpu-server-report (systemd on GPU hosts) |
| [dockers](dockers/) | Compose files and Dockerfiles |

## Production

**Central stack** (one host, bundled Traefik on `gsad_traefik` network):

```bash
cp dockers/.env.example .env
# Set SPRING_PROFILES_ACTIVE=prod, GSAD_PUBLIC_HOST, ACME_EMAIL, strong secrets
# DNS for GSAD_PUBLIC_HOST must point at this host; open ports 80 and 443
docker compose -f compose.yaml -f dockers/compose.prod.yaml --profile prod up -d --build
```

Traefik terminates HTTPS (Let's Encrypt); `/api/internal/*` is blocked on :443. GPU agents call `http://<central-host-ip>:8080` directly (not the public HTTPS URL).

**Local prod-like stack** (HTTP only, no certificate):

```bash
# In .env: SPRING_PROFILES_ACTIVE=prod, GSAD_PUBLIC_HOST=localhost
docker compose -f compose.yaml -f dockers/compose.prod.yaml -f dockers/compose.prod-local.yaml --profile prod up -d --build
```

Then open `http://localhost/` (UI) and `http://localhost/api/*` (public API).

**GPU hosts:** deploy [server-agent](server-agent/) on each machine. Set `REPORT_API_URL=http://<central-host-ip>:8080`, plus `AGENT_PSK` and `AGENT_SERVER_ID`.

Prod Flyway is schema-only — servers register via agent report API. DB backup: `backend/gsad/deploy/scripts/backup-postgres.sh`.

## Configuration (`.env`)

| Variable | Description |
|----------|-------------|
| `SPRING_PROFILES_ACTIVE` | `dev` (default) or `prod` |
| `GSAD_PUBLIC_HOST` | Public hostname for Traefik (prod); use `localhost` for prod-local |
| `ACME_EMAIL` | Let's Encrypt email (prod HTTPS) |
| `BACKEND_AGENT_PORT` | Host port exposed for GPU agent internal API (default `8080`) |
| `AGENT_PSK` | `X-Agent-PSK` for internal APIs |
| `JWT_SECRET` | JWT signing key (≥32 chars in prod) |
| `DB_PASSWORD` / `REDIS_PASSWORD` | Data store passwords |

Template: `cp dockers/.env.example .env`

## Tests

```bash
cd backend/gsad && ./mvnw test
```

More detail: [backend/gsad/README.md](backend/gsad/README.md)
