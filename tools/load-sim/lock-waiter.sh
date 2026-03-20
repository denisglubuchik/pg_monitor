#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

TARGET_DB_NAME="$(resolve_target_db "${1:-}")"

cat <<'SQL' | run_sql "${TARGET_DB_NAME}"
BEGIN;
UPDATE lock_test SET v = v + 1 WHERE id = 1;
COMMIT;
SQL

echo "lock waiter completed in ${TARGET_DB_NAME} (if holder was running, this waited for lock release)"
