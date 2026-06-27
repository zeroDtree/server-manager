#!/usr/bin/env bash

# @help-begin
# Generate random secrets in repo-root .env (≥32 chars, hex).
# Creates .env from .env.example if missing. Skips keys already set to non-placeholder values.
#
# Usage:
#   ./secret.sh
#
# Example:
#   cp .env.example .env && ./utils/secret.sh
# @help-end

# @help-options-begin
#   -h, --help              show help
# @help-options-end

set -euo pipefail

log() { printf 'secret: %s\n' "$*"; }
die() { printf 'secret: ERROR: %s\n' "$*" >&2; exit 1; }

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
ENV_EXAMPLE="${REPO_ROOT}/.env.example"
ENV_FILE="${REPO_ROOT}/.env"

SECRET_KEYS=(
  DB_PASSWORD
  REDIS_PASSWORD
  JWT_SECRET
  AGENT_MASTER_SECRET
  CREDENTIALS_ENCRYPTION_KEY
)

placeholder_for() {
  printf 'change-me-%s-at-least-32-chars' "$1"
}

get_env_value() {
  local key="$1"
  grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

needs_generation() {
  local key="$1" value="$2" placeholder
  placeholder="$(placeholder_for "$key")"
  [[ -z "$value" || "$value" == "$placeholder" ]]
}

generate_secret() {
  openssl rand -hex 32
}

set_env_value() {
  local key="$1" value="$2"
  local tmp found=0
  tmp="$(mktemp)"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^${key}= ]]; then
      printf '%s=%s\n' "$key" "$value" >>"$tmp"
      found=1
    else
      printf '%s\n' "$line" >>"$tmp"
    fi
  done <"$ENV_FILE"
  if [[ "$found" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$value" >>"$tmp"
  fi
  mv "$tmp" "$ENV_FILE"
}

cd "$REPO_ROOT"

if [[ ! -f "$ENV_EXAMPLE" ]]; then
  die "missing ${ENV_EXAMPLE}"
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_EXAMPLE" "$ENV_FILE"
  log "created .env from .env.example"
fi

command -v openssl >/dev/null 2>&1 || die "openssl is required"

generated=()
skipped=()

for key in "${SECRET_KEYS[@]}"; do
  value="$(get_env_value "$key")"
  if needs_generation "$key" "$value"; then
    set_env_value "$key" "$(generate_secret)"
    generated+=("$key")
  else
    skipped+=("$key")
  fi
done

chmod 600 "$ENV_FILE"

if ((${#generated[@]} > 0)); then
  log "generated: ${generated[*]}"
fi
if ((${#skipped[@]} > 0)); then
  log "skipped (already set): ${skipped[*]}"
fi
if ((${#generated[@]} == 0 && ${#skipped[@]} == 0)); then
  log "no secret keys processed"
fi
