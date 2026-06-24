#!/usr/bin/env bash

# @help-begin
# Install gsad-backup-postgres systemd timer (substitutes @REPO_ROOT@ from this clone).
# Requires root.
#
# Usage:
#   sudo ./install-backup-timer.sh
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
    *) printf 'ERROR: Unexpected argument: %s (see --help)\n' "$arg" >&2; exit 1 ;;
  esac
done

SERVICE="gsad-backup-postgres.service"
TIMER="gsad-backup-postgres.timer"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SYSTEMD_SRC="${SCRIPT_DIR}/systemd"

log() { printf '==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    die "Run as root: sudo $0"
  fi
}

install_unit() {
  local unit="$1"
  local src="${SYSTEMD_SRC}/${unit}"
  local dest="/etc/systemd/system/${unit}"

  [[ -f "${src}" ]] || die "Missing unit template: ${src}"
  sed "s|@REPO_ROOT@|${REPO_ROOT}|g" "${src}" > "${dest}"
  chmod 644 "${dest}"
  log "Installed ${dest}"
}

main() {
  require_root
  install_unit "${SERVICE}"
  install_unit "${TIMER}"
  systemctl daemon-reload
  systemctl enable --now "${TIMER}"
  log "Backup timer enabled (repo: ${REPO_ROOT})"
  log "Check: systemctl status ${TIMER}"
}

main "$@"
