#!/usr/bin/env bash

# @help-begin
# Deploy GSAD production stack (HTTPS) or local-prod stack (HTTP on localhost).
# Runs preflight, secret.sh, docker compose up, waits for backend health, optional first admin.
#
# First login requires an admin user: set ADMIN_EMAIL on deploy, or run create-prod-admin.sh
# immediately after deploy.
#
# Stack mode: --local / --external / --prod flags override everything; otherwise reads
# .gsad-compose-mode (written by a prior deploy), then defaults to prod.
#
# Usage:
#   ./deploy-prod.sh
#   ./deploy-prod.sh --local
#   ./deploy-prod.sh --external
#
# Env: ADMIN_EMAIL — create first admin after deploy (recommended)
# Env: ADMIN_PASSWORD — forwarded to create-prod-admin.sh (never written to .env)
# Env: GSAD_PUBLIC_HOST, ACME_EMAIL, BACKEND_AGENT_BIND — from repo-root .env; secrets from .env.secrets
# Env (external): TRAEFIK_EXTERNAL_NETWORK, TRAEFIK_ENTRYPOINT, TRAEFIK_CERT_RESOLVER — see docs/external-traefik.md
#
# Example:
#   ADMIN_EMAIL=admin@example.com ./deploy-prod.sh
#   ./deploy-prod.sh --local --no-admin
#   ADMIN_EMAIL=admin@example.com ./deploy-prod.sh --external
# @help-end

# @help-options-begin
#   --local                 local-prod HTTP stack (localhost)
#   --external              prod stack using an existing edge Traefik (no bundled Traefik)
#   --prod                  bundled Traefik prod stack (override persisted mode)
#   --no-build              skip image build on up
#   --no-admin              skip create-prod-admin.sh
#   -h, --help              show help
# @help-options-end

set -euo pipefail

LOCAL_MODE=0
EXTERNAL_MODE=0
DO_BUILD=1
DO_ADMIN=1
GSAD_COMPOSE_MODE_SET=""

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

set_compose_mode_from_flag() {
  local flag="$1"
  local mode="$2"
  if [[ -n "$GSAD_COMPOSE_MODE_SET" && "$GSAD_COMPOSE_MODE_SET" != "$flag" ]]; then
    printf 'deploy-prod: ERROR: --%s and --%s are mutually exclusive\n' \
      "$GSAD_COMPOSE_MODE_SET" "$flag" >&2
    exit 1
  fi
  GSAD_COMPOSE_MODE="$mode"
  GSAD_COMPOSE_MODE_SET="$flag"
}

for arg in "$@"; do
  case "$arg" in
    --local) set_compose_mode_from_flag local local ;;
    --external) set_compose_mode_from_flag external external ;;
    --prod) set_compose_mode_from_flag prod prod ;;
    --no-build) DO_BUILD=0 ;;
    --no-admin) DO_ADMIN=0 ;;
    -h|--help) usage ;;
    *) printf 'deploy-prod: ERROR: unexpected argument: %s (see --help)\n' "$arg" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GSAD_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=lib/compose.sh
source "${SCRIPT_DIR}/lib/compose.sh"

gsad_resolve_compose_mode
gsad_normalize_compose_mode_for_deploy
export GSAD_COMPOSE_MODE

LOCAL_MODE=0
EXTERNAL_MODE=0
case "${GSAD_COMPOSE_MODE}" in
  local) LOCAL_MODE=1 ;;
  external) EXTERNAL_MODE=1 ;;
  prod) ;;
  *)
    printf 'deploy-prod: ERROR: unsupported deploy mode: %s\n' "${GSAD_COMPOSE_MODE}" >&2
    exit 1
    ;;
esac

log() { printf 'deploy-prod: %s\n' "$*"; }
die() { printf 'deploy-prod: ERROR: %s\n' "$*" >&2; exit 1; }

admin_create_hint() {
  if [[ "$EXTERNAL_MODE" -eq 1 ]]; then
    printf '  ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh --external\n'
  elif [[ "$LOCAL_MODE" -eq 1 ]]; then
    printf '  ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh --local\n'
  else
    printf '  ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh\n'
  fi
}

notice_no_admin() {
  printf '%s\n' \
    'deploy-prod: NOTICE: no admin user — login will fail until you create one:'
  admin_create_hint
}

wait_backend_healthy() {
  local max=120 interval=5 elapsed=0 health
  while (( elapsed < max )); do
    health="$(gsad_compose ps --status running --format '{{.Health}}' backend 2>/dev/null | head -1 | tr -d '[:space:]')"
    if [[ "$health" == "healthy" ]]; then
      return 0
    fi
    if gsad_compose exec -T backend curl -sf http://localhost:8080/actuator/health >/dev/null 2>&1; then
      return 0
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
  return 1
}

cd "$GSAD_REPO_ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  log "created .env from .env.example"
fi

preflight_args=()
if [[ "$LOCAL_MODE" -eq 1 ]]; then
  preflight_args+=(--local)
fi
if [[ "$EXTERNAL_MODE" -eq 1 ]]; then
  preflight_args+=(--external)
fi
if ! "${SCRIPT_DIR}/preflight.sh" "${preflight_args[@]}"; then
  die "preflight failed — fix issues above and retry"
fi

gsad_load_env

if [[ "$LOCAL_MODE" -eq 1 && "${GSAD_PUBLIC_HOST:-}" != "localhost" ]]; then
  log "WARNING: GSAD_PUBLIC_HOST is '${GSAD_PUBLIC_HOST:-}' — local-prod expects localhost"
fi

"${SCRIPT_DIR}/secret.sh"

up_args=(up -d)
if [[ "$DO_BUILD" -eq 1 ]]; then
  up_args+=(--build)
fi
log "starting stack (mode=${GSAD_COMPOSE_MODE})"
gsad_compose "${up_args[@]}"

log "waiting for backend health (up to 120s)"
if ! wait_backend_healthy; then
  die "backend did not become healthy — check: ./utils/gsad-compose.sh logs backend"
fi
log "backend is healthy"

if [[ "$DO_ADMIN" -eq 1 && -n "${ADMIN_EMAIL:-}" ]]; then
  log "creating first admin (idempotent)"
  admin_args=()
  if [[ "$LOCAL_MODE" -eq 1 ]]; then
    admin_args+=(--local)
  elif [[ "$EXTERNAL_MODE" -eq 1 ]]; then
    admin_args+=(--external)
  fi
  SPRING_PROFILES_ACTIVE=prod "${SCRIPT_DIR}/create-prod-admin.sh" "${admin_args[@]}"
elif [[ "$DO_ADMIN" -eq 0 ]]; then
  log "skipping admin bootstrap (--no-admin)"
fi

if ! gsad_has_admin; then
  notice_no_admin
fi

if [[ "$LOCAL_MODE" -eq 1 ]]; then
  ui_url="http://localhost/"
else
  ui_url="https://${GSAD_PUBLIC_HOST}/"
fi

gsad_write_compose_mode "${GSAD_COMPOSE_MODE}"

log "deploy complete"
printf '%s\n' \
  "" \
  "  UI: ${ui_url}" \
  "  Next: Admin → Import servers → docs/agent-psk.md → server-agent/" \
  "        Admin → Import users" \
  "        Restrict BACKEND_AGENT_PORT to GPU/VPN CIDR" \
  "        Backups: docs/backup.md" \
  ""
