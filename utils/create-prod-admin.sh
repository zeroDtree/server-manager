#!/usr/bin/env bash

# @help-begin
# Create the first production admin user (idempotent).
# Run from the repo root after the stack is up and postgres is healthy.
#
# Usage:
#   ./create-prod-admin.sh
#
# Env: ADMIN_EMAIL — admin email (required)
# Env: ADMIN_PASSWORD — plain password; prompts if unset (do not store in .env)
# Env: ADMIN_LINUX_USERNAME — Linux username (default: gsadadmin)
# Env: ADMIN_DISPLAY_NAME — display name (default: Admin)
# Env: COMPOSE_FILE — optional docker compose file override
# Env: SPRING_PROFILES_ACTIVE — selects compose files when COMPOSE_FILE is unset
#
# Examples:
#   ADMIN_EMAIL=admin@example.com ./utils/create-prod-admin.sh
#   ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='secret' ./utils/create-prod-admin.sh
# @help-end

# @help-options-begin
#   -h, --help              show help
# @help-options-end

set -euo pipefail

log() { printf 'create-prod-admin: %s\n' "$*"; }
die() { printf 'create-prod-admin: ERROR: %s\n' "$*" >&2; exit 1; }

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

LINUX_USERNAME_PATTERN='^[a-z_][a-z0-9_-]{0,31}$'

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

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${ADMIN_EMAIL:-}" ]]; then
  die "ADMIN_EMAIL is required (see --help)"
fi

ADMIN_LINUX_USERNAME="${ADMIN_LINUX_USERNAME:-gsadadmin}"
ADMIN_DISPLAY_NAME="${ADMIN_DISPLAY_NAME:-Admin}"

if [[ ! "$ADMIN_LINUX_USERNAME" =~ $LINUX_USERNAME_PATTERN ]]; then
  die "Invalid ADMIN_LINUX_USERNAME: ${ADMIN_LINUX_USERNAME} (must match ${LINUX_USERNAME_PATTERN})"
fi

if ! compose_cmd ps --status running postgres 2>/dev/null | grep -q postgres; then
  die "postgres container is not running; start the stack first"
fi

admin_count="$(compose_cmd exec -T postgres psql -U gsad -d gsad -tAc \
  "SELECT COUNT(*) FROM t_user WHERE roles ~ '(^|,)admin(,|$)';")"
admin_count="$(echo "$admin_count" | tr -d '[:space:]')"

if [[ "${admin_count:-0}" -gt 0 ]]; then
  log "admin user already exists (${admin_count}); skipping"
  exit 0
fi

if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
  read -r -s -p "Admin password: " ADMIN_PASSWORD
  echo
  read -r -s -p "Confirm password: " ADMIN_PASSWORD_CONFIRM
  echo
  if [[ "$ADMIN_PASSWORD" != "$ADMIN_PASSWORD_CONFIRM" ]]; then
    die "Passwords do not match"
  fi
fi

if [[ ${#ADMIN_PASSWORD} -lt 8 ]]; then
  die "Password must be at least 8 characters"
fi

email_exists="$(compose_cmd exec -T postgres psql -U gsad -d gsad -tAc \
  "SELECT COUNT(*) FROM t_user WHERE lower(email) = lower($(escape_sql_literal "$ADMIN_EMAIL"));")"
email_exists="$(echo "$email_exists" | tr -d '[:space:]')"

if [[ "${email_exists:-0}" -gt 0 ]]; then
  die "email already exists: ${ADMIN_EMAIL}"
fi

linux_exists="$(compose_cmd exec -T postgres psql -U gsad -d gsad -tAc \
  "SELECT COUNT(*) FROM t_user WHERE linux_username = $(escape_sql_literal "$ADMIN_LINUX_USERNAME");")"
linux_exists="$(echo "$linux_exists" | tr -d '[:space:]')"

if [[ "${linux_exists:-0}" -gt 0 ]]; then
  die "linux_username already exists: ${ADMIN_LINUX_USERNAME}"
fi

sql_email="$(escape_sql_literal "$ADMIN_EMAIL")"
sql_pass="$(escape_sql_literal "$ADMIN_PASSWORD")"
sql_linux="$(escape_sql_literal "$ADMIN_LINUX_USERNAME")"
sql_display="$(escape_sql_literal "$ADMIN_DISPLAY_NAME")"

compose_cmd exec -T postgres psql -U gsad -d gsad -v ON_ERROR_STOP=1 <<SQL
CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO t_user (email, password, roles, linux_username, status, display_name)
SELECT ${sql_email}, crypt(${sql_pass}, gen_salt('bf', 10)), 'admin', ${sql_linux}, 'ACTIVE', ${sql_display}
WHERE NOT EXISTS (
  SELECT 1 FROM t_user WHERE roles ~ '(^|,)admin(,|$)'
);
SQL

inserted="$(compose_cmd exec -T postgres psql -U gsad -d gsad -tAc \
  "SELECT COUNT(*) FROM t_user WHERE lower(email) = lower(${sql_email});")"
inserted="$(echo "$inserted" | tr -d '[:space:]')"

if [[ "${inserted:-0}" -ne 1 ]]; then
  die "failed to create admin user"
fi

log "created admin: ${ADMIN_EMAIL} (linux_username=${ADMIN_LINUX_USERNAME})"
log "log in via the UI or POST /api/auth/login, then change the password at Account → Change password (sidebar)"
