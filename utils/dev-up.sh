#!/usr/bin/env bash

# @help-begin
# Start the dev Docker stack (mock profile, host-bound backend/Postgres/Redis).
# Creates .env and .env.secrets if missing, then runs compose up --build.
#
# Usage:
#   ./dev-up.sh
#   ./dev-up.sh -d
#
# Example:
#   ./dev-up.sh -d
#   cd gsad-frontend && npm install && npm run dev
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
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GSAD_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GSAD_COMPOSE_MODE=dev

# shellcheck source=lib/compose.sh
source "${SCRIPT_DIR}/lib/compose.sh"

log() { printf 'dev-up: %s\n' "$*"; }

cd "$GSAD_REPO_ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  log "created .env from .env.example"
fi

"${SCRIPT_DIR}/secret.sh"

log "starting dev stack (profile=mock)"
gsad_compose up --build "$@"
gsad_write_compose_mode dev
