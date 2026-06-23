#!/usr/bin/env bash
#
# Register a GPU server in production (required before agents can report metrics).
# Run from the repo root when postgres is healthy.
#
# Environment:
#   SERVER_ID          (required) e.g. gpu-01
#   RESOURCE_LEVEL     (required) e.g. H100
#   SSH_HOST           (optional) management IP/hostname
#   COMPOSE_FILE       Optional docker compose file override
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() { printf 'register-server: %s\n' "$*"; }
die() { printf 'register-server: ERROR: %s\n' "$*" >&2; exit 1; }

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

: "${SERVER_ID:?Set SERVER_ID (e.g. gpu-01)}"
: "${RESOURCE_LEVEL:?Set RESOURCE_LEVEL (e.g. H100)}"

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
