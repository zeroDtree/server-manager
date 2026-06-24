# Development

## Quick start

```bash
cp dockers/.env.example .env
docker compose --profile mock up --build
cd gsad-frontend && npm install && npm run dev
```

`compose.override.yaml` merges [`dockers/compose.dev.yaml`](../dockers/compose.dev.yaml) automatically — backend, Postgres, and Redis bind to the host. The `mock` profile starts two dev agent containers (`account-provision-mock`, `gpu-server-report-mock`) that simulate up to **100** servers each (`MOCK_SERVER_COUNT` in [`dockers/compose.yaml`](../dockers/compose.yaml)).

| URL                                   | Purpose                       |
| ------------------------------------- | ----------------------------- |
| http://localhost:5173                 | Vue UI (Vite dev server)      |
| http://localhost:8080/api/*           | Backend API                   |
| http://localhost:8080/swagger-ui.html | Swagger UI (dev profile only) |
| http://localhost:8080/v3/api-docs     | OpenAPI JSON (live)           |

Vite proxies `/api` to `http://localhost:8080` ([`gsad-frontend/vite.config.ts`](../gsad-frontend/vite.config.ts)).

## Seed data

Flyway `dev` profile: admin `admin@gsad.local` / `Admin@123456`; mock servers `gpu-mock-001` … `gpu-mock-100`. After migration changes: `docker compose down -v`, then re-up.
