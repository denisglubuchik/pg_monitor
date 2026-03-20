#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${PROJECT_ROOT}/docker/compose/compose.yaml}"
DEFAULT_TARGET_DB="monitored_db"
DEFAULT_DB_IDENTIFIER_HOST="postgres"
DEFAULT_DB_IDENTIFIER_PORT="5432"

compose() {
  docker compose -f "${COMPOSE_FILE}" "$@"
}

run_sql() {
  local db_name="$1"
  shift
  if [[ -n "${TARGET_PG_DSN:-}" ]]; then
    psql "${TARGET_PG_DSN}" -v ON_ERROR_STOP=1 -d "${db_name}" "$@"
    return
  fi

  local db_service
  db_service="$(resolve_compose_db_service)"
  compose exec -T "${db_service}" psql -v ON_ERROR_STOP=1 -U postgres -d "${db_name}" "$@"
}

resolve_target_db() {
  local explicit_db="${1:-}"
  if [[ -n "${explicit_db}" ]]; then
    echo "${explicit_db}"
    return
  fi

  if [[ -n "${TARGET_DB:-}" ]]; then
    echo "${TARGET_DB}"
    return
  fi

  echo "${DEFAULT_TARGET_DB}"
}

resolve_target_db_identifier() {
  local explicit_value="${1:-}"
  local candidate="${explicit_value:-${TARGET_DB_IDENTIFIER:-}}"
  if [[ -n "${candidate}" && "${candidate}" == *"@"* ]]; then
    echo "${candidate}"
    return
  fi

  local db_name="${candidate:-$(resolve_target_db "")}"
  local host="${DB_IDENTIFIER_HOST:-${DEFAULT_DB_IDENTIFIER_HOST}}"
  local port="${DB_IDENTIFIER_PORT:-${DEFAULT_DB_IDENTIFIER_PORT}}"
  echo "${db_name}@${host}:${port}"
}

resolve_compose_db_service() {
  if [[ -n "${COMPOSE_DB_SERVICE:-}" ]]; then
    echo "${COMPOSE_DB_SERVICE}"
    return
  fi

  local services
  services="$(compose config --services 2>/dev/null || true)"
  if [[ -z "${services}" ]]; then
    echo "unable to detect compose DB service; set COMPOSE_DB_SERVICE" >&2
    return 1
  fi

  local preferred
  for preferred in postgres db database; do
    if echo "${services}" | grep -qx "${preferred}"; then
      echo "${preferred}"
      return
    fi
  done

  local guessed
  guessed="$(
    echo "${services}" \
      | grep -E "(postgres|^db$|db-|db_|-db|_db|database|^pg$|pg-)" \
      | head -n 1 \
      || true
  )"
  if [[ -n "${guessed}" ]]; then
    echo "${guessed}"
    return
  fi

  if [[ "$(echo "${services}" | wc -l | tr -d ' ')" -eq 1 ]]; then
    echo "${services}"
    return
  fi

  echo "unable to detect compose DB service; set COMPOSE_DB_SERVICE" >&2
  return 1
}
