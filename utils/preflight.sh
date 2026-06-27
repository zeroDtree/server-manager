#!/usr/bin/env bash

# @help-begin
# Pre-deploy checks for GSAD production or local-prod Docker stacks.
# Run from the repo root before ./utils/deploy-prod.sh.
#
# Usage:
#   ./preflight.sh
#   ./preflight.sh --local
#
# Example:
#   ./preflight.sh --strict
# @help-end

# @help-options-begin
#   --local                 validate local-prod stack (HTTP on localhost)
#   --strict                treat warnings as errors
#   -h, --help              show help
# @help-options-end

set -euo pipefail

LOCAL_MODE=0
STRICT=0

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --local) LOCAL_MODE=1 ;;
    --strict) STRICT=1 ;;
    -h|--help) usage ;;
    *) printf 'preflight: ERROR: unexpected argument: %s (see --help)\n' "$arg" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GSAD_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GSAD_COMPOSE_MODE=prod
if [[ "$LOCAL_MODE" -eq 1 ]]; then
  GSAD_COMPOSE_MODE=local
fi

# shellcheck source=lib/compose.sh
source "${SCRIPT_DIR}/lib/compose.sh"

ENV_FILE="${GSAD_REPO_ROOT}/.env"
ENV_EXAMPLE="${GSAD_REPO_ROOT}/.env.example"
SECRETS_FILE="${GSAD_REPO_ROOT}/.env.secrets"

errors=0
warnings=0

ok() { printf 'preflight: OK: %s\n' "$*"; }
warn() {
  printf 'preflight: WARNING: %s\n' "$*"
  warnings=$((warnings + 1))
}
fail() {
  printf 'preflight: ERROR: %s\n' "$*"
  errors=$((errors + 1))
}

get_env_value() {
  local key="$1" file="$2"
  grep -E "^${key}=" "$file" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

is_placeholder_secret() {
  local key="$1" value="$2"
  [[ -z "$value" || "$value" == "change-me-${key}-at-least-32-chars" ]]
}

port_in_use() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -H -ltn "sport = :${port}" 2>/dev/null | grep -q .
    return
  fi
  if command -v lsof >/dev/null 2>&1; then
    lsof -i ":${port}" -sTCP:LISTEN -t >/dev/null 2>&1
    return
  fi
  return 1
}

cd "$GSAD_REPO_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  fail "docker not found on PATH"
fi
if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose not available"
fi

for path in gsad-backend/pom.xml gsad-frontend/package.json; do
  if [[ ! -f "$path" ]]; then
    fail "missing submodule file: $path (run: git submodule update --init --recursive)"
  fi
done

if [[ ! -f "$ENV_FILE" && ! -f "$ENV_EXAMPLE" ]]; then
  fail "missing .env and .env.example"
fi

if [[ -f "$ENV_FILE" ]]; then
  if ! gsad_compose config >/dev/null 2>&1; then
    fail "docker compose config failed (check .env and compose files)"
  else
    ok "docker compose config valid"
  fi
else
  _gsad_compose_file_args
  if ! docker compose "${GSAD_COMPOSE_FILE_ARGS[@]}" --env-file "$ENV_EXAMPLE" --profile prod config >/dev/null 2>&1; then
    fail "docker compose config failed (check .env.example and compose files)"
  else
    ok "docker compose config valid (.env.example)"
  fi
fi

check_file="$ENV_FILE"
if [[ ! -f "$check_file" ]]; then
  check_file="$ENV_EXAMPLE"
fi

gsad_load_env

bind="${BACKEND_AGENT_BIND:-$(get_env_value BACKEND_AGENT_BIND "$check_file")}"
bind="${bind:-127.0.0.1}"
if [[ -z "${bind// }" ]]; then
  fail "BACKEND_AGENT_BIND is required in .env"
fi

host="${GSAD_PUBLIC_HOST:-$(get_env_value GSAD_PUBLIC_HOST "$check_file")}"
if [[ -z "${host// }" ]]; then
  fail "GSAD_PUBLIC_HOST is required in .env"
fi

if [[ "$LOCAL_MODE" -eq 1 ]]; then
  if [[ "$host" != "localhost" ]]; then
    warn "GSAD_PUBLIC_HOST is '${host}' — local-prod expects localhost"
  fi
else
  acme="${ACME_EMAIL:-$(get_env_value ACME_EMAIL "$check_file")}"
  if [[ -z "${acme// }" ]]; then
    fail "ACME_EMAIL is required in .env for production TLS"
  fi
fi

if [[ "$bind" == "127.0.0.1" ]]; then
  warn "BACKEND_AGENT_BIND=127.0.0.1 — remote GPU agents need RFC1918 or NetBird bind (see README Agent access & security)"
fi

if port_in_use 80; then
  warn "port 80 is already in use on this host"
fi
if [[ "$LOCAL_MODE" -eq 0 ]] && port_in_use 443; then
  warn "port 443 is already in use on this host"
fi

if [[ -f "$ENV_FILE" && "$host" == "gsad.example.com" ]]; then
  warn "GSAD_PUBLIC_HOST is still gsad.example.com — set your real hostname in .env"
fi

if [[ -f "$SECRETS_FILE" ]]; then
  for key in DB_PASSWORD REDIS_PASSWORD JWT_SECRET AGENT_MASTER_SECRET CREDENTIALS_ENCRYPTION_KEY; do
    value="$(get_env_value "$key" "$SECRETS_FILE")"
    if is_placeholder_secret "$key" "$value"; then
      warn "${key} is unset or placeholder in .env.secrets — run ./utils/secret.sh"
    fi
  done
elif [[ -f "$ENV_FILE" ]]; then
  warn "missing .env.secrets — run ./utils/secret.sh"
fi

if [[ "$errors" -gt 0 ]]; then
  printf 'preflight: failed with %d error(s), %d warning(s)\n' "$errors" "$warnings"
  exit 1
fi

if [[ "$STRICT" -eq 1 && "$warnings" -gt 0 ]]; then
  printf 'preflight: failed with %d warning(s) (--strict)\n' "$warnings"
  exit 1
fi

printf 'preflight: passed (%d warning(s))\n' "$warnings"
exit 0
