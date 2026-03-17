#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_ROOT}/docker/compose/compose.yaml}"

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

run_sql() {
  local db_name="$1"
  shift
  compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d "${db_name}" "$@"
}
