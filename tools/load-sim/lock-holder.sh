#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

SLEEP_SECONDS="${1:-300}"
if ! [[ "${SLEEP_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${SLEEP_SECONDS}" -le 0 ]]; then
  echo "usage: $0 [positive_sleep_seconds] [target_db]" >&2
  exit 1
fi

TARGET_DB_NAME="$(resolve_target_db "${2:-}")"

cat <<SQL | run_sql "${TARGET_DB_NAME}"
BEGIN;
UPDATE lock_test SET v = v + 1 WHERE id = 1;
SELECT pg_sleep(${SLEEP_SECONDS});
COMMIT;
SQL

echo "lock holder completed after ${SLEEP_SECONDS}s in ${TARGET_DB_NAME}"
