#!/usr/bin/env bash
set -euo pipefail

REQUESTS="${1:-300}"
BASE_URL="${2:-http://localhost:8000}"

if ! [[ "${REQUESTS}" =~ ^[0-9]+$ ]] || [[ "${REQUESTS}" -le 0 ]]; then
  echo "usage: $0 [positive_requests] [base_url]" >&2
  exit 1
fi

for _ in $(seq 1 "${REQUESTS}"); do
  curl -fsS "${BASE_URL}/healthz" > /dev/null
  curl -fsS "${BASE_URL}/metrics" > /dev/null
  curl -fsS "${BASE_URL}/analytics/queries/weekly-top?db_identifier=monitored_db&limit=20" > /dev/null || true
  curl -fsS "${BASE_URL}/analytics/queries/week-over-week?db_identifier=monitored_db&limit=20" > /dev/null || true
done

echo "http burst completed: ${REQUESTS} rounds against ${BASE_URL}"
