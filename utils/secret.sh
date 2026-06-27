#!/usr/bin/env bash

# @help-begin
# Generate random secrets in repo-root .env.secrets (≥32 chars, hex).
# Creates .env.secrets from .env.secrets.example if missing. Skips keys already set to non-placeholder values.
# Migrates secret keys from legacy single-file .env on first run.
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
ENV_FILE="${REPO_ROOT}/.env"
SECRETS_EXAMPLE="${REPO_ROOT}/.env.secrets.example"
SECRETS_FILE="${REPO_ROOT}/.env.secrets"

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
  local key="$1" file="$2"
  grep -E "^${key}=" "$file" 2>/dev/null | tail -1 | cut -d= -f2- || true
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
  local key="$1" value="$2" file="$3"
  local tmp found=0
  tmp="$(mktemp)"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^${key}= ]]; then
      printf '%s=%s\n' "$key" "$value" >>"$tmp"
      found=1
    else
      printf '%s\n' "$line" >>"$tmp"
    fi
  done <"$file"
  if [[ "$found" -eq 0 ]]; then
    printf '%s=%s\n' "$key" "$value" >>"$tmp"
  fi
  mv "$tmp" "$file"
}

remove_env_key() {
  local key="$1" file="$2"
  local tmp
  tmp="$(mktemp)"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" =~ ^${key}= ]]; then
      continue
    fi
    printf '%s\n' "$line" >>"$tmp"
  done <"$file"
  mv "$tmp" "$file"
}

migrate_secrets_from_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    return 0
  fi

  local key value migrated=0
  for key in "${SECRET_KEYS[@]}"; do
    value="$(get_env_value "$key" "$ENV_FILE")"
    if [[ -n "$value" ]] && ! needs_generation "$key" "$value"; then
      set_env_value "$key" "$value" "$SECRETS_FILE"
      remove_env_key "$key" "$ENV_FILE"
      migrated=1
    elif [[ -n "$value" ]]; then
      remove_env_key "$key" "$ENV_FILE"
      migrated=1
    fi
  done

  if [[ "$migrated" -eq 1 ]]; then
    log "migrated secrets from .env to .env.secrets"
  fi
}

cd "$REPO_ROOT"

if [[ ! -f "$SECRETS_EXAMPLE" ]]; then
  die "missing ${SECRETS_EXAMPLE}"
fi

if [[ ! -f "$SECRETS_FILE" ]]; then
  cp "$SECRETS_EXAMPLE" "$SECRETS_FILE"
  log "created .env.secrets from .env.secrets.example"
fi

migrate_secrets_from_env

command -v openssl >/dev/null 2>&1 || die "openssl is required"

generated=()
skipped=()

for key in "${SECRET_KEYS[@]}"; do
  value="$(get_env_value "$key" "$SECRETS_FILE")"
  if needs_generation "$key" "$value"; then
    set_env_value "$key" "$(generate_secret)" "$SECRETS_FILE"
    generated+=("$key")
  else
    skipped+=("$key")
  fi
done

chmod 600 "$SECRETS_FILE"

if ((${#generated[@]} > 0)); then
  log "generated: ${generated[*]}"
fi
if ((${#skipped[@]} > 0)); then
  log "skipped (already set): ${skipped[*]}"
fi
if ((${#generated[@]} == 0 && ${#skipped[@]} == 0)); then
  log "no secret keys processed"
fi
