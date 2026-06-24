#!/usr/bin/env bash

# @help-begin
# Derive per-server AGENT_PSK (hex) from the backend master secret via HMAC-SHA256.
# Master secret is read interactively — never from env or argv. Requires a TTY.
# Prints only the derived hex to stdout (safe for AGENT_PSK=$(...) capture).
#
# Usage:
#   ./derive-agent-psk.sh <serverId>
#
# Example:
#   AGENT_PSK=$(./derive-agent-psk.sh gpu-node-01)
# @help-end

# @help-options-begin
#   -h, --help              show help
# @help-options-end

set -euo pipefail

MIN_MASTER_SECRET_LENGTH=32

log() { printf 'derive-agent-psk: %s\n' "$*" >&2; }
die() { printf 'derive-agent-psk: ERROR: %s\n' "$*" >&2; exit 1; }

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

if [[ $# -lt 1 ]]; then
  usage
fi

if [[ $# -gt 1 ]]; then
  die "Unexpected arguments (see --help)"
fi

server_id="$1"

if [[ -n "${AGENT_MASTER_SECRET:-}" ]]; then
  log "WARNING: AGENT_MASTER_SECRET is set in the environment; ignoring it (enter secret at prompt)"
fi

if [[ ! -r /dev/tty ]]; then
  die "Interactive terminal required; run this script directly on a TTY"
fi

read -rsp "Agent master secret: " master_secret </dev/tty
printf '\n' >&2
read -rsp "Confirm master secret: " master_secret_confirm </dev/tty
printf '\n' >&2

if [[ "$master_secret" != "$master_secret_confirm" ]]; then
  unset master_secret master_secret_confirm
  die "Master secrets do not match"
fi
unset master_secret_confirm

if [[ ${#master_secret} -lt $MIN_MASTER_SECRET_LENGTH ]]; then
  unset master_secret
  die "Master secret must be at least ${MIN_MASTER_SECRET_LENGTH} characters"
fi

printf '%s' "$server_id" | openssl dgst -sha256 -hmac "$master_secret" -hex | awk '{print $2}'

unset master_secret
