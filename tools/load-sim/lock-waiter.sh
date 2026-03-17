#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

cat <<'SQL' | compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d monitored_db
BEGIN;
UPDATE lock_test SET v = v + 1 WHERE id = 1;
COMMIT;
SQL

echo "lock waiter completed (if holder was running, this waited for lock release)"
