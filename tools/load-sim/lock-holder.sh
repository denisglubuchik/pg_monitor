#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

SLEEP_SECONDS="${1:-300}"
if ! [[ "${SLEEP_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${SLEEP_SECONDS}" -le 0 ]]; then
  echo "usage: $0 [positive_sleep_seconds]" >&2
  exit 1
fi

cat <<SQL | compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d monitored_db
BEGIN;
UPDATE lock_test SET v = v + 1 WHERE id = 1;
SELECT pg_sleep(${SLEEP_SECONDS});
COMMIT;
SQL

echo "lock holder completed after ${SLEEP_SECONDS}s"
