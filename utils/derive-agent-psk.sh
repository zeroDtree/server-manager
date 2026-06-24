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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/agent-psk.sh"

AGENT_PSK_LOG_PREFIX=derive-agent-psk

log() { agent_psk_log "$@"; }
die() { agent_psk_die "$@"; }

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

agent_psk_read_master_secret
agent_psk_derive_hex "$server_id" "$master_secret"
unset master_secret
