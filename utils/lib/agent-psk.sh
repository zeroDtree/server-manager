# Shared agent PSK derivation helpers. Source from derive-agent-psk*.sh — do not execute directly.

AGENT_PSK_MIN_MASTER_SECRET_LENGTH=32

agent_psk_log() {
  printf '%s: %s\n' "${AGENT_PSK_LOG_PREFIX:-derive-agent-psk}" "$*" >&2
}

agent_psk_die() {
  printf '%s: ERROR: %s\n' "${AGENT_PSK_LOG_PREFIX:-derive-agent-psk}" "$*" >&2
  exit 1
}

agent_psk_trim() {
  local value="$1"
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  printf '%s' "$value"
}

agent_psk_read_master_secret() {
  if [[ -n "${AGENT_MASTER_SECRET:-}" ]]; then
    agent_psk_log "WARNING: AGENT_MASTER_SECRET is set in the environment; ignoring it (enter secret at prompt)"
  fi

  if [[ ! -r /dev/tty ]]; then
    agent_psk_die "Interactive terminal required; run this script directly on a TTY"
  fi

  read -rsp "Agent master secret: " master_secret </dev/tty
  printf '\n' >&2
  read -rsp "Confirm master secret: " master_secret_confirm </dev/tty
  printf '\n' >&2

  if [[ "$master_secret" != "$master_secret_confirm" ]]; then
    unset master_secret master_secret_confirm
    agent_psk_die "Master secrets do not match"
  fi
  unset master_secret_confirm

  if [[ ${#master_secret} -lt $AGENT_PSK_MIN_MASTER_SECRET_LENGTH ]]; then
    unset master_secret
    agent_psk_die "Master secret must be at least ${AGENT_PSK_MIN_MASTER_SECRET_LENGTH} characters"
  fi
}

agent_psk_derive_hex() {
  local server_id
  server_id="$(agent_psk_trim "$1")"
  local master_secret="$2"

  if [[ -z "$server_id" ]]; then
    agent_psk_die "server_id is required"
  fi

  printf '%s' "$server_id" | openssl dgst -sha256 -hmac "$master_secret" -hex | awk '{print $NF}'
}
