#!/usr/bin/env bash

# @help-begin
# Register a GPU server in t_server (required before agents can report metrics).
# Run from the repo root when postgres is healthy.
#
# Usage:
#   ./register-server.sh
#
# Env: SERVER_ID — server id, e.g. gpu-01 (required)
# Env: RESOURCE_LEVEL — GPU tier label, e.g. H100 (required)
# Env: SSH_HOST — optional management IP or hostname
# Env: COMPOSE_FILE — optional docker compose file override
# Env: SPRING_PROFILES_ACTIVE — selects compose files when COMPOSE_FILE is unset
# @help-end

# @help-options-begin
#   -h, --help              show help
# @help-options-end

set -euo pipefail

log() { printf 'register-server: %s\n' "$*"; }
die() { printf 'register-server: ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage ;;
    *) die "Unexpected argument: $arg (see --help)" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

escape_sql_literal() {
  local s="$1"
  s="${s//\'/\'\'}"
  printf "'%s'" "$s"
}

compose_cmd() {
  local args=()
  if [[ -n "${COMPOSE_FILE:-}" ]]; then
    local f
    read -r -a files <<< "${COMPOSE_FILE}"
    for f in "${files[@]}"; do
      args+=(-f "$f")
    done
  elif [[ "${SPRING_PROFILES_ACTIVE:-dev}" == "prod" ]]; then
    args=(-f compose.yaml -f dockers/compose.prod.yaml)
  else
    args=(-f compose.yaml)
  fi
  docker compose "${args[@]}" "$@"
}

cd "$REPO_ROOT"

if [[ -z "${SERVER_ID:-}" ]]; then
  die "SERVER_ID is required (see --help)"
fi
if [[ -z "${RESOURCE_LEVEL:-}" ]]; then
  die "RESOURCE_LEVEL is required (see --help)"
fi

if ! compose_cmd ps --status running postgres 2>/dev/null | grep -q postgres; then
  die "postgres container is not running; start the stack first"
fi

server_id_sql="$(escape_sql_literal "$SERVER_ID")"
resource_sql="$(escape_sql_literal "$RESOURCE_LEVEL")"
ssh_host_sql="NULL"
if [[ -n "${SSH_HOST:-}" ]]; then
  ssh_host_sql="$(escape_sql_literal "$SSH_HOST")"
fi

compose_cmd exec -T postgres psql -U gsad -d gsad -v ON_ERROR_STOP=1 <<SQL
INSERT INTO t_server (server_id, ssh_host, resource_level, status, metrics_json)
VALUES (${server_id_sql}, ${ssh_host_sql}, ${resource_sql}, 'OFFLINE', '{}'::jsonb)
ON CONFLICT (server_id) DO UPDATE
SET resource_level = EXCLUDED.resource_level,
    ssh_host = COALESCE(EXCLUDED.ssh_host, t_server.ssh_host),
    updated_at = NOW();
SQL

log "registered server ${SERVER_ID} (${RESOURCE_LEVEL})"
