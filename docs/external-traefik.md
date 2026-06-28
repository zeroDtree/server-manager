# External edge Traefik

Use this when the host already runs an edge Traefik on **80/443** (e.g. NetBird `netbird-traefik`). GSAD starts **postgres**, **redis**, **backend**, and **frontend** only; your Traefik routes HTTPS to them via Docker labels.

Agent traffic is unchanged: GPU hosts call `http://<central-host>:8080/api/internal/*` directly — never through Traefik. See [Agent network and security](agent-network.md).

## Prerequisites

Your edge Traefik must:

- Use the **Docker provider** with `exposedByDefault=false`
- Share a Docker **network** with GSAD containers (same network as `--providers.docker.network`)
- Expose HTTPS on an entrypoint matching `TRAEFIK_ENTRYPOINT` (default `websecure`)
- Use a certificate resolver matching `TRAEFIK_CERT_RESOLVER` (default `letsencrypt`)

## Configure `.env`

```ini
GSAD_PUBLIC_HOST=gsad.example.com
BACKEND_AGENT_BIND=10.206.0.8          # NetBird or private IP — not 127.0.0.1 for remote agents
BACKEND_AGENT_PORT=8080

TRAEFIK_EXTERNAL_NETWORK=netbird       # Docker network name
TRAEFIK_ENTRYPOINT=websecure           # match your Traefik entrypoint
TRAEFIK_CERT_RESOLVER=letsencrypt      # match your Traefik cert resolver
```

`ACME_EMAIL` is not used in external mode — TLS is handled by your edge Traefik.

### NetBird reference

Typical NetBird Traefik settings that work with GSAD defaults:

| NetBird Traefik | GSAD `.env` |
| --- | --- |
| `--providers.docker.network=netbird` | `TRAEFIK_EXTERNAL_NETWORK=netbird` |
| `--entrypoints.websecure.address=:443` | `TRAEFIK_ENTRYPOINT=websecure` |
| `--certificatesresolvers.letsencrypt...` | `TRAEFIK_CERT_RESOLVER=letsencrypt` |

DNS ACME on the edge (e.g. Tencent Cloud) is fine — GSAD only needs `Host()` router labels.

### Find the Docker network name

```bash
docker inspect netbird-traefik --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{"\n"}}{{end}}'
```

## Deploy

```bash
./utils/preflight.sh --external
ADMIN_EMAIL=admin@example.com ./utils/deploy-prod.sh --external
```

Verify no GSAD Traefik container is running:

```bash
./utils/gsad-compose.sh --external ps
```

## Verify routing and security

```bash
curl -Ik "https://${GSAD_PUBLIC_HOST}/"
curl -Ik "https://${GSAD_PUBLIC_HOST}/api/internal/servers/provision/pending"
```

The internal API path must **not** reach the backend on HTTPS (blocked by the `gsad-block` router at the edge).

## Upgrade

```bash
git pull && git submodule update --init --recursive && \
  ./utils/deploy-prod.sh --external --no-admin
```

## Local HTTP stack

`deploy-prod.sh --local` still starts bundled Traefik on port **80** and conflicts with an existing edge Traefik. On the same host, use `--external` instead of `--local`.
