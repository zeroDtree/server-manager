#!/usr/bin/env bash

# @help-begin
# Run docker compose with repo env, compose files, and profile for prod, local-prod, or dev.
#
# Usage:
#   ./gsad-compose.sh [options] [compose args...]
#
# Examples:
#   ./gsad-compose.sh ps
#   ./gsad-compose.sh --local down -v
#   ./gsad-compose.sh --dev logs -f backend
#   ./gsad-compose.sh exec -T backend curl -sS http://localhost:8080/actuator/health
# @help-end

# @help-options-begin
#   --local                 local-prod HTTP stack (localhost)
#   --dev                   dev stack (mock profile + compose.override)
#   -h, --help              show help
# @help-options-end

set -euo pipefail

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GSAD_REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GSAD_COMPOSE_MODE=prod

compose_args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --local) GSAD_COMPOSE_MODE=local; shift ;;
    --dev) GSAD_COMPOSE_MODE=dev; shift ;;
    -h|--help) usage ;;
    --) shift; compose_args+=("$@"); break ;;
    *) compose_args+=("$1"); shift ;;
  esac
done

# shellcheck source=lib/compose.sh
source "${SCRIPT_DIR}/lib/compose.sh"

cd "$GSAD_REPO_ROOT"
gsad_compose "${compose_args[@]}"
