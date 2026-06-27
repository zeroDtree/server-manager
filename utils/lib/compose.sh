# Shared Docker Compose helpers for GSAD stacks (prod, local-prod, dev).
# Source from utils/*.sh — set GSAD_REPO_ROOT and GSAD_COMPOSE_MODE before calling gsad_compose.
#
# GSAD_COMPOSE_MODE: prod (default) | local | dev

: "${GSAD_COMPOSE_MODE:=prod}"

if [[ -z "${GSAD_REPO_ROOT:-}" ]]; then
  printf 'compose: ERROR: GSAD_REPO_ROOT must be set before sourcing compose.sh\n' >&2
  return 1 2>/dev/null || exit 1
fi

_gsad_compose_file_args() {
  GSAD_COMPOSE_FILE_ARGS=()
  GSAD_COMPOSE_PROFILE=

  case "${GSAD_COMPOSE_MODE}" in
    dev)
      GSAD_COMPOSE_PROFILE=mock
      ;;
    local)
      GSAD_COMPOSE_FILE_ARGS=(
        -f "${GSAD_REPO_ROOT}/compose.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod-local.yaml"
      )
      GSAD_COMPOSE_PROFILE=prod
      ;;
    prod)
      GSAD_COMPOSE_FILE_ARGS=(
        -f "${GSAD_REPO_ROOT}/compose.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod.yaml"
      )
      GSAD_COMPOSE_PROFILE=prod
      ;;
    *)
      printf 'compose: ERROR: unknown GSAD_COMPOSE_MODE=%s (use prod, local, or dev)\n' \
        "${GSAD_COMPOSE_MODE}" >&2
      return 1 2>/dev/null || exit 1
      ;;
  esac
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
  if ((${#GSAD_COMPOSE_FILE_ARGS[@]} > 0)); then
    docker compose "${GSAD_COMPOSE_FILE_ARGS[@]}" --profile "${GSAD_COMPOSE_PROFILE}" "$@"
  else
    docker compose --profile "${GSAD_COMPOSE_PROFILE}" "$@"
  fi
}

gsad_admin_count() {
  gsad_compose exec -T postgres psql -U gsad -d gsad -tAc \
    "SELECT COUNT(*) FROM t_user WHERE roles ~ '(^|,)admin(,|$)';" 2>/dev/null \
    | tr -d '[:space:]' || true
}

gsad_has_admin() {
  local count
  count="$(gsad_admin_count)"
  [[ "${count:-0}" -gt 0 ]]
}
