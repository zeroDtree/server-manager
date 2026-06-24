#!/usr/bin/env bash

# @help-begin
# Derive per-server AGENT_PSK (hex) for many hosts from a CSV file.
# Master secret is read interactively once — never from env or argv. Requires a TTY.
#
# Usage:
#   ./derive-agent-psk-batch.sh servers.csv
#   ./derive-agent-psk-batch.sh -o agents-with-psk.csv servers.csv
#
# Input CSV: header row required; column server_id (case-insensitive) is required.
# Optional columns are preserved in output. Commas inside field values are not supported.
#
# Output CSV: input columns plus agent_psk. Default destination is stdout; use -o to write a file.
# Progress and summary go to stderr. Output contains secrets — chmod 600 and do not commit.
#
# Example input:
#   server_id,ssh_host
#   gpu-node-01,10.0.0.11
#   gpu-node-02,10.0.0.12
# @help-end

# @help-options-begin
#   -o, --output FILE       write CSV to FILE instead of stdout
#   -h, --help              show help
# @help-options-end

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/agent-psk.sh"

AGENT_PSK_LOG_PREFIX=derive-agent-psk-batch

log() { agent_psk_log "$@"; }
die() { agent_psk_die "$@"; }

usage() {
  awk '/^# @help-begin$/{f=1; next} /^# @help-end$/{f=0} f' "$0"
  printf '%s\n' '#' 'Options:' '#'
  awk '/^# @help-options-begin$/{f=1; next} /^# @help-options-end$/{f=0} f' "$0"
  exit 0
}

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

read_csv_field_at() {
  local fields_csv="$1"
  local index="$2"
  local -a fields=()
  IFS=',' read -r -a fields <<<"$fields_csv"
  if (( index < 0 || index >= ${#fields[@]} )); then
    printf ''
    return
  fi
  printf '%s' "${fields[$index]}"
}

csv_escape_field() {
  local value="$1"
  value="${value//\"/\"\"}"
  if [[ "$value" == *","* || "$value" == *"\""* || "$value" == *$'\n'* || "$value" == *$'\r'* ]]; then
    printf '"%s"' "$value"
  else
    printf '%s' "$value"
  fi
}

write_csv_line() {
  local sink="$1"
  shift
  local -a fields=("$@")
  local i
  local line=""
  for (( i = 0; i < ${#fields[@]}; i++ )); do
    if (( i > 0 )); then
      line+=','
    fi
    line+="$(csv_escape_field "${fields[$i]}")"
  done
  printf '%s\n' "$line" >>"$sink"
}

server_id_seen() {
  local needle="$1"
  local id
  for id in "${seen_server_ids[@]}"; do
    if [[ "$id" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

output_file=""
csv_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    -o|--output)
      if [[ $# -lt 2 ]]; then
        die "Missing value for $1"
      fi
      output_file="$2"
      shift 2
      ;;
    --)
      shift
      break
      ;;
    -*)
      die "Unknown option: $1 (see --help)"
      ;;
    *)
      if [[ -n "$csv_path" ]]; then
        die "Unexpected argument: $1 (see --help)"
      fi
      csv_path="$1"
      shift
      ;;
  esac
done

if [[ -z "$csv_path" ]]; then
  usage
fi

if [[ ! -f "$csv_path" ]]; then
  die "CSV file not found: ${csv_path}"
fi

if [[ ! -s "$csv_path" ]]; then
  die "CSV file is empty: ${csv_path}"
fi

agent_psk_read_master_secret

declare -a header_fields=()
server_id_index=-1
declare -a seen_server_ids=()
derived_count=0

header_line=""
if ! IFS= read -r header_line || [[ -z "${header_line//[[:space:]]/}" ]]; then
  unset master_secret
  die "CSV file is missing a header row"
fi

IFS=',' read -r -a header_fields <<<"$header_line"
for (( i = 0; i < ${#header_fields[@]}; i++ )); do
  header_fields[$i]="$(agent_psk_trim "${header_fields[$i]}")"
  if [[ "$(to_lower "${header_fields[$i]}")" == "server_id" ]]; then
    if (( server_id_index >= 0 )); then
      unset master_secret
      die "CSV header contains duplicate server_id column"
    fi
    server_id_index=$i
  fi
done

if (( server_id_index < 0 )); then
  unset master_secret
  die "CSV header is missing required column: server_id"
fi

output_header=("${header_fields[@]}" "agent_psk")

if [[ -n "$output_file" ]]; then
  : >"$output_file"
  write_csv_line "$output_file" "${output_header[@]}"
  csv_sink="$output_file"
else
  write_csv_line /dev/stdout "${output_header[@]}"
  csv_sink=/dev/stdout
fi

row_number=1
while IFS= read -r line || [[ -n "$line" ]]; do
  row_number=$((row_number + 1))
  if [[ -z "${line//[[:space:]]/}" ]]; then
    continue
  fi

  declare -a row_fields=()
  IFS=',' read -r -a row_fields <<<"$line"
  server_id="$(agent_psk_trim "$(read_csv_field_at "$line" "$server_id_index")")"
  if [[ -z "$server_id" ]]; then
    unset master_secret
    die "Row ${row_number}: server_id is required"
  fi
  if server_id_seen "$server_id"; then
    unset master_secret
    die "Row ${row_number}: duplicate server_id in CSV: ${server_id}"
  fi
  seen_server_ids+=("$server_id")

  agent_psk="$(agent_psk_derive_hex "$server_id" "$master_secret")"
  output_row=("${row_fields[@]}" "$agent_psk")
  write_csv_line "$csv_sink" "${output_row[@]}"
  derived_count=$((derived_count + 1))
done <"$csv_path"

unset master_secret

if (( derived_count == 0 )); then
  die "No data rows found in CSV"
fi

log "derived ${derived_count} PSK(s)"
if [[ -n "$output_file" ]]; then
  log "wrote ${output_file} (contains secrets — chmod 600 and do not commit)"
fi
