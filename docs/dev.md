# Development

Run the central stack with mock GPU agents, and the Vue UI on Vite.

## Quick start

```bash
./utils/dev-up.sh -d
cd gsad-frontend && npm install && npm run dev
```

Open `http://localhost:5173`. The Vite dev server proxies `/api` to `VITE_PROXY_TARGET` (default `http://localhost:8080`).

Seeded admin: `admin@gsad.local` / `Admin@123456`.

The top-right **Language** control switches 中文 / English. Capture English manuals with `GSAD_DOCS_LOCALE=en` and Chinese manuals with `GSAD_DOCS_LOCALE=zh`.

## What the mock stack provides

`./utils/dev-up.sh` starts Docker Compose in **dev** mode (`--profile mock`):

- Backend (Spring `dev` profile), PostgreSQL, Redis
- Flyway `dev` seed: admin above; mock servers `gpu-mock-001` … `gpu-mock-100` with shared agent PSK `dev-mock-agent-psk-0001`
- `account-provision-mock` — grants/revokes Linux-style access against the backend
- `gpu-server-report-mock` — reports fake GPU metrics so the resource board has data

After migration changes:

```bash
./utils/gsad-compose.sh --dev down -v
./utils/dev-up.sh -d
```

## Host port conflicts

Dev compose publishes Postgres **5432**, Redis **6379**, and the backend **8080** on the host. If those ports are already in use, override them:

```bash
GSAD_DEV_POSTGRES_PORT=15432 \
GSAD_DEV_REDIS_PORT=16380 \
GSAD_DEV_BACKEND_PORT=18080 \
  ./utils/dev-up.sh -d

cd gsad-frontend && VITE_PROXY_TARGET=http://localhost:18080 npm run dev
```

## Preview these docs

```bash
cd docs && npm install && npm run dev
```

VitePress serves the manuals (screenshots under `docs/assets/en/` and `docs/assets/zh/`) at the printed local URL. The site root is English; `/zh/` is Chinese.

### Recapture screenshots

Manuals use 1440×900 (2×) PNG shots of the console. With the UI on `:5173` and Playwright available:

```bash
# once: npm install playwright && npx playwright install chromium
PLAYWRIGHT_ROOT=/path/to/playwright-install \
  GSAD_DOCS_LOCALE=en \
  node docs/scripts/capture-screenshots.mjs

PLAYWRIGHT_ROOT=/path/to/playwright-install \
  GSAD_DOCS_LOCALE=zh \
  node docs/scripts/capture-screenshots.mjs
```

The script writes kebab-case files such as `board.png`, `application-detail.png`, and `admin-users-import.png` into `docs/assets/<locale>/`. Do not screenshot OS file pickers; the in-app import modal is enough. Keep agent PSKs masked.

## Tests

```bash
cd gsad-backend && ./mvnw test
cd gsad-frontend && npm run lint && npm run typecheck && npm test
```
