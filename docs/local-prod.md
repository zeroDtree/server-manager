# Local prod-like stack (HTTP only)

**Languages:** [English](local-prod.md) · [简体中文](local-prod.zh-CN.md)

Run the production compose files on localhost without TLS — useful for validating images and routing before real DNS and Let's Encrypt.

## Start

```bash
SPRING_PROFILES_ACTIVE=prod GSAD_PUBLIC_HOST=localhost docker compose \
  -f compose.yaml \
  -f dockers/compose.prod.yaml \
  -f dockers/compose.prod-local.yaml \
  --profile prod up -d --build
```

Open `http://localhost/` (UI) and `http://localhost/api/*` (public API).

After `backend` and `postgres` are healthy, create the first admin — see [First admin](../README.md#first-admin) in the main README.

## Reset (clean DB)

Use when switching from dev/mock or re-testing bootstrap. Use the **same** `-f` files and `--profile prod` as start, or Compose may target the wrong project/volumes:

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
