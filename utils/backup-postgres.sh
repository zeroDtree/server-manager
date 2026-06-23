#!/usr/bin/env bash
#
# Backup gsad PostgreSQL: dump, gzip, verify, retention + total size cap.
# Run from the repo root (or via cron/systemd with WorkingDirectory set).
#
# Environment:
#   BACKUP_DIR         Output directory (default: <repo>/backups)
#   RETENTION_DAYS     Delete backups older than N days (default: 30)
#   MAX_TOTAL_MB       Max total backup dir size in MB (default: 500)
#   COMPOSE_FILE       Optional docker compose file override
#
# Requires GNU find (-printf) for size-based pruning; typical prod hosts are Linux.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${DB_PASSWORD:?Set DB_PASSWORD in .env}"

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
