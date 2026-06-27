#!/usr/bin/env bash

# @help-begin
# Backup gsad PostgreSQL: pg_dump, gzip, verify, retention and total size cap.
# Run from the repo root (or via cron/systemd with WorkingDirectory set).
# Requires GNU find (-printf) for size-based pruning; typical prod hosts are Linux.
#
# Usage:
#   ./backup-postgres.sh
#
# Env: BACKUP_DIR — output directory (default: <repo>/backups)
# Env: RETENTION_DAYS — delete backups older than N days (default: 30)
# Env: MAX_TOTAL_MB — max total backup dir size in MB (default: 500)
# Env: COMPOSE_FILE — optional docker compose file override
# Env: SPRING_PROFILES_ACTIVE — selects compose files when COMPOSE_FILE is unset
# Env: DB_PASSWORD — from repo root .env.secrets (required)
# @help-end

# @help-options-begin
#   -h, --help              show help
# @help-options-end

set -euo pipefail

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    -h|--help) usage ;;
    *) printf 'backup-postgres: ERROR: Unexpected argument: %s (see --help)\n' "$arg" >&2; exit 1 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="${REPO_ROOT}/utils"
GSAD_REPO_ROOT="$REPO_ROOT"
GSAD_COMPOSE_MODE=prod

# shellcheck source=lib/compose.sh
source "${SCRIPT_DIR}/lib/compose.sh"
OUT_DIR="${BACKUP_DIR:-$REPO_ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
MAX_TOTAL_MB="${MAX_TOTAL_MB:-500}"
MAX_TOTAL_BYTES=$((MAX_TOTAL_MB * 1024 * 1024))

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

gsad_load_env

if [[ -z "${DB_PASSWORD:-}" ]]; then
  printf 'backup-postgres: ERROR: DB_PASSWORD is required in .env.secrets (see --help)\n' >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
OUT_FILE="$OUT_DIR/gsad_$(date +%Y%m%d_%H%M%S).sql.gz"
LOCK="$OUT_DIR/.backup.lock"

exec 9>"$LOCK"
flock -n 9 || { echo "backup-postgres: already running" >&2; exit 1; }

total_backup_bytes() {
  local total=0 f size
  shopt -s nullglob
  for f in "$OUT_DIR"/gsad_*.sql.gz; do
    size=$(wc -c < "$f" | tr -d ' ')
    total=$((total + size))
  done
  shopt -u nullglob
  echo "$total"
}

prune_by_age() {
  find "$OUT_DIR" -maxdepth 1 -name 'gsad_*.sql.gz' -type f -mtime +"${RETENTION_DAYS}" -delete
}

prune_by_total_size() {
  local total oldest
  while (( $(total_backup_bytes) > MAX_TOTAL_BYTES )); do
    oldest=$(find "$OUT_DIR" -maxdepth 1 -name 'gsad_*.sql.gz' -type f -printf '%T@ %p\n' \
      | sort -n | head -1 | cut -d' ' -f2-)
    if [[ -z "$oldest" ]]; then
      echo "backup-postgres: cannot prune below ${MAX_TOTAL_MB}MB cap" >&2
      exit 1
    fi
    rm -f "$oldest"
  done
}

compose_cmd exec -T postgres \
  pg_dump -U gsad --no-owner --no-acl gsad | gzip -9 > "$OUT_FILE"

gzip -t "$OUT_FILE"

new_size=$(wc -c < "$OUT_FILE" | tr -d ' ')
if (( new_size > MAX_TOTAL_BYTES )); then
  rm -f "$OUT_FILE"
  echo "backup-postgres: backup alone exceeds ${MAX_TOTAL_MB}MB limit (${new_size} bytes)" >&2
  exit 1
fi

prune_by_age
prune_by_total_size

echo "backup-postgres: wrote $OUT_FILE (dir total: $(total_backup_bytes) bytes)"
