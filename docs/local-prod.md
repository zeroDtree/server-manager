# Local prod-like stack (HTTP only)

Run the production compose files on localhost without TLS — useful for validating images and routing before real DNS and Let's Encrypt.

## Start

Set `GSAD_PUBLIC_HOST=localhost` in `.env`, then deploy:

```bash
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local
```

Open `http://localhost/` (UI) and `http://localhost/api/*` (public API).

`deploy-prod.sh` runs preflight, creates `.env.secrets`, waits for backend health, and creates the first admin when `ADMIN_EMAIL` is set.

## Reset (clean DB)

Use when switching from dev/mock or re-testing bootstrap:

```bash
./utils/gsad-compose.sh --local down -v
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --local
```

**`down -v` deletes `postgres_data`** (and other named volumes in this project). Dev seed admin (`admin@gsad.local`) and mock servers are removed.

## Host with existing edge Traefik

`--local` starts bundled Traefik on port **80** and conflicts with NetBird or other edge Traefik on the same host. Use [External edge Traefik](external-traefik.md) (`deploy-prod.sh --external`) instead.
