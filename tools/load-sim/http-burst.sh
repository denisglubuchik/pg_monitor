#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

REQUESTS="${1:-300}"
BASE_URL="${2:-http://localhost:8000}"
TARGET_DB_OR_IDENTIFIER="${3:-}"
TARGET_DB_IDENTIFIER="$(resolve_target_db_identifier "${TARGET_DB_OR_IDENTIFIER}")"

if ! [[ "${REQUESTS}" =~ ^[0-9]+$ ]] || [[ "${REQUESTS}" -le 0 ]]; then
  echo "usage: $0 [positive_requests] [base_url] [target_db_or_db_identifier]" >&2
  exit 1
fi

for _ in $(seq 1 "${REQUESTS}"); do
  curl -fsS "${BASE_URL}/healthz" > /dev/null
  curl -fsS "${BASE_URL}/metrics" > /dev/null
  curl -fsS "${BASE_URL}/analytics/queries/weekly-top?db_identifier=${TARGET_DB_IDENTIFIER}&limit=20" > /dev/null || true
  curl -fsS "${BASE_URL}/analytics/queries/week-over-week?db_identifier=${TARGET_DB_IDENTIFIER}&limit=20" > /dev/null || true
done

echo "http burst completed: ${REQUESTS} rounds against ${BASE_URL} for ${TARGET_DB_IDENTIFIER}"
