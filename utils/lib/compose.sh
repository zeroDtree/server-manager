# Shared Docker Compose helpers for GSAD stacks (prod, local-prod, external, dev).
# Source from utils/*.sh — set GSAD_REPO_ROOT before calling gsad_compose.
#
# GSAD_COMPOSE_MODE: prod (default) | local | external | dev
# Resolution (when not set by caller flag): env override > .gsad-compose-mode > prod

if [[ -z "${GSAD_REPO_ROOT:-}" ]]; then
  printf 'compose: ERROR: GSAD_REPO_ROOT must be set before sourcing compose.sh\n' >&2
  return 1 2>/dev/null || exit 1
fi

gsad_compose_mode_file() {
  printf '%s/.gsad-compose-mode' "${GSAD_REPO_ROOT}"
}

gsad_valid_compose_mode() {
  case "$1" in
    prod|local|external|dev) return 0 ;;
    *) return 1 ;;
  esac
}

gsad_read_persisted_compose_mode() {
  local file mode
  file="$(gsad_compose_mode_file)"
  [[ -f "$file" ]] || return 1
  mode="$(tr -d '[:space:]' < "$file")"
  if gsad_valid_compose_mode "$mode"; then
    printf '%s' "$mode"
    return 0
  fi
  printf 'compose: WARNING: invalid mode in %s: %q\n' "$file" "$mode" >&2
  return 1
}

gsad_write_compose_mode() {
  local mode="$1"
  if ! gsad_valid_compose_mode "$mode"; then
    printf 'compose: ERROR: invalid compose mode for write: %q\n' "$mode" >&2
    return 1 2>/dev/null || exit 1
  fi
  printf '%s\n' "$mode" > "$(gsad_compose_mode_file)"
}

gsad_resolve_compose_mode() {
  local mode="${GSAD_COMPOSE_MODE:-}"
  mode="${mode//[$'\t\r\n ']/}"
  if [[ -n "$mode" ]]; then
    if ! gsad_valid_compose_mode "$mode"; then
      printf 'compose: ERROR: unknown GSAD_COMPOSE_MODE=%s (use prod, local, external, or dev)\n' \
        "$mode" >&2
      return 1 2>/dev/null || exit 1
    fi
    GSAD_COMPOSE_MODE="$mode"
    return 0
  fi
  if mode="$(gsad_read_persisted_compose_mode)"; then
    GSAD_COMPOSE_MODE="$mode"
    return 0
  fi
  GSAD_COMPOSE_MODE=prod
}

_gsad_compose_file_args() {
  GSAD_COMPOSE_FILE_ARGS=()

  case "${GSAD_COMPOSE_MODE}" in
    dev)
      ;;
    local)
      GSAD_COMPOSE_FILE_ARGS=(
        -f "${GSAD_REPO_ROOT}/compose.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod-local.yaml"
      )
      ;;
    external)
      GSAD_COMPOSE_FILE_ARGS=(
        -f "${GSAD_REPO_ROOT}/compose.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.edge-external.yaml"
      )
      ;;
    prod)
      GSAD_COMPOSE_FILE_ARGS=(
        -f "${GSAD_REPO_ROOT}/compose.yaml"
        -f "${GSAD_REPO_ROOT}/dockers/compose.prod.yaml"
      )
      ;;
    *)
      printf 'compose: ERROR: unknown GSAD_COMPOSE_MODE=%s (use prod, local, external, or dev)\n' \
        "${GSAD_COMPOSE_MODE}" >&2
      return 1 2>/dev/null || exit 1
      ;;
  esac
}

_gsad_compose_profile_args() {
  GSAD_COMPOSE_PROFILE_ARGS=()

  case "${GSAD_COMPOSE_MODE}" in
    dev)
      GSAD_COMPOSE_PROFILE_ARGS=(--profile mock)
      ;;
    external)
      GSAD_COMPOSE_PROFILE_ARGS=(--profile prod)
      ;;
    prod|local)
      GSAD_COMPOSE_PROFILE_ARGS=(--profile prod --profile bundled-edge)
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
  _gsad_compose_profile_args
  if ((${#GSAD_COMPOSE_FILE_ARGS[@]} > 0)); then
    docker compose "${GSAD_COMPOSE_FILE_ARGS[@]}" "${GSAD_COMPOSE_PROFILE_ARGS[@]}" "$@"
  else
    docker compose "${GSAD_COMPOSE_PROFILE_ARGS[@]}" "$@"
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
