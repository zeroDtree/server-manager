# Shared Docker Compose helpers for GSAD production stacks.
# Source from utils/*.sh — set GSAD_REPO_ROOT and GSAD_COMPOSE_MODE before calling gsad_compose.

: "${GSAD_COMPOSE_MODE:=prod}"

if [[ -z "${GSAD_REPO_ROOT:-}" ]]; then
  printf 'compose: ERROR: GSAD_REPO_ROOT must be set before sourcing compose.sh\n' >&2
  return 1 2>/dev/null || exit 1
fi

_gsad_compose_file_args() {
  GSAD_COMPOSE_FILE_ARGS=(
    -f "${GSAD_REPO_ROOT}/compose.yaml"
    -f "${GSAD_REPO_ROOT}/dockers/compose.prod.yaml"
  )
  if [[ "${GSAD_COMPOSE_MODE}" == "local" ]]; then
    GSAD_COMPOSE_FILE_ARGS+=(-f "${GSAD_REPO_ROOT}/dockers/compose.prod-local.yaml")
  fi
}

gsad_load_env() {
  set -a
  if [[ -f "${GSAD_REPO_ROOT}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${GSAD_REPO_ROOT}/.env"
  fi
  if [[ -f "${GSAD_REPO_ROOT}/.env.secrets" ]]; then
    # shellcheck disable=SC1091
    source "${GSAD_REPO_ROOT}/.env.secrets"
  fi
  set +a
}

gsad_compose() {
  gsad_load_env
  _gsad_compose_file_args
  docker compose "${GSAD_COMPOSE_FILE_ARGS[@]}" --profile prod "$@"
}
