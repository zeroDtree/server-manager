#!/usr/bin/env bash

# @help-begin
# Dev mock GPU server report loop (Docker). Posts synthetic metrics to the backend.
# Env-driven; normally invoked as the container CMD.
#
# Usage:
#   ./report-loop.sh
#
# Env: REPORT_API_URL — backend base URL (default: http://backend:8080)
# Env: AGENT_MASTER_SECRET — HMAC master secret for per-server PSK (default: change-me-in-production)
# Env: AGENT_REPORT_INTERVAL — seconds between report cycles (default: 30)
# Env: MOCK_SERVER_COUNT — number of mock servers (default: 100)
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
    *) printf '[gpu-server-report-mock] ERROR: Unexpected argument: %s (see --help)\n' "$arg" >&2; exit 1 ;;
  esac
done

REPORT_API_URL="${REPORT_API_URL:-http://backend:8080}"
AGENT_MASTER_SECRET="${AGENT_MASTER_SECRET:-change-me-in-production}"
AGENT_REPORT_INTERVAL="${AGENT_REPORT_INTERVAL:-${INTERVAL_SEC:-30}}"
MOCK_SERVER_COUNT="${MOCK_SERVER_COUNT:-100}"

derive_agent_psk() {
  local server_id="$1"
  printf '%s' "$server_id" | openssl dgst -sha256 -hmac "$AGENT_MASTER_SECRET" -hex | awk '{print $2}'
}

report_server() {
  local server_id="$1"
  local resource_level="$2"
  local gpu_count="$3"
  local avg_util="$4"
  local avg_mem="$5"
  local gpu_name="$6"
  local mem_total_mb="$7"
  local agent_psk

  agent_psk="$(derive_agent_psk "$server_id")"

  local collected_at gpus_json
  collected_at="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  gpus_json="$(build_gpus_json "$gpu_count" "$avg_util" "$avg_mem" "$gpu_name" "$mem_total_mb")"

  curl -sf -X POST "${REPORT_API_URL}/api/internal/servers/report" \
    -H "Content-Type: application/json" \
    -H "X-Agent-Server-Id: ${server_id}" \
    -H "X-Agent-PSK: ${agent_psk}" \
    -d "{
      \"serverId\": \"${server_id}\",
      \"resourceLevel\": \"${resource_level}\",
      \"collectedAt\": \"${collected_at}\",
      \"summary\": {
        \"gpuCount\": ${gpu_count},
        \"avgUtil\": ${avg_util},
        \"avgMemUsedMb\": ${avg_mem}
      },
      \"gpus\": ${gpus_json}
    }" >/dev/null
  echo "[gpu-server-report-mock] reported ${server_id}"
}

build_gpus_json() {
  local count="$1"
  local avg_util="$2"
  local avg_mem="$3"
  local gpu_name="$4"
  local mem_total_mb="$5"
  local rows=()
  local i mem_used util

  for ((i = 0; i < count; i++)); do
    util="$(awk -v base="$avg_util" -v idx="$i" 'BEGIN { printf "%.2f", base + ((idx % 3) - 1) * 0.03 }')"
    mem_used="$(awk -v util="$util" -v total="$mem_total_mb" 'BEGIN { printf "%d", int(util * total) }')"
    rows+=("{\"index\":${i},\"name\":\"${gpu_name}\",\"avgUtil\":${util},\"memUsedMb\":${mem_used},\"memTotalMb\":${mem_total_mb}}")
  done

  local IFS=,
  echo "[${rows[*]}]"
}

# index (1-based) -> resource_level|gpu_count|gpu_name|mem_total_mb
mock_server_spec() {
  local i="$1"
  case $(( (i - 1) % 5 )) in
    0) echo "H100|8|NVIDIA H100|81920" ;;
    1) echo "A100|4|NVIDIA A100|81920" ;;
    2) echo "L40S|2|NVIDIA L40S|49152" ;;
    3) echo "L4|1|NVIDIA L4|24576" ;;
    4) echo "T4|1|NVIDIA T4|16384" ;;
  esac
}

report_all_mock_servers() {
  local i spec resource_level gpu_count gpu_name mem_total_mb
  local server_id avg_util avg_mem

  for i in $(seq 1 "$MOCK_SERVER_COUNT"); do
    server_id="$(printf "gpu-mock-%03d" "$i")"

    IFS='|' read -r resource_level gpu_count gpu_name mem_total_mb <<< "$(mock_server_spec "$i")"

    # Deterministic util/mem per index (0.18 .. 0.88)
    avg_util="$(awk -v n="$i" 'BEGIN { printf "%.2f", 0.18 + ((n - 1) % 8) * 0.10 }')"
    avg_mem="$(awk -v util="$avg_util" -v total="$mem_total_mb" -v count="$gpu_count" \
      'BEGIN { printf "%d", int(util * total * count / (count > 0 ? count : 1)) }')"

    report_server "$server_id" "$resource_level" "$gpu_count" \
      "$avg_util" "$avg_mem" "$gpu_name" "$mem_total_mb"
  done
}

echo "[gpu-server-report-mock] targeting ${REPORT_API_URL}, interval ${AGENT_REPORT_INTERVAL}s, servers=${MOCK_SERVER_COUNT}"

echo "[gpu-server-report-mock] waiting for backend..."
until curl -sf "${REPORT_API_URL}/actuator/health" >/dev/null; do
  sleep 2
done
echo "[gpu-server-report-mock] backend is ready"

while true; do
  report_all_mock_servers
  sleep "${AGENT_REPORT_INTERVAL}"
done
