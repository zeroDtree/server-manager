#!/usr/bin/env bash
#
# Install gsad-backup-postgres systemd timer (substitutes @REPO_ROOT@ from this clone).
#
# Example:
#   sudo ./utils/install-backup-timer.sh
#
set -euo pipefail

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
