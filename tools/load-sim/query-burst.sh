#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

ITERATIONS="${1:-500}"
if ! [[ "${ITERATIONS}" =~ ^[0-9]+$ ]] || [[ "${ITERATIONS}" -le 0 ]]; then
  echo "usage: $0 [positive_iterations]" >&2
  exit 1
fi

cat <<SQL | compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d monitored_db
SELECT format(
  'INSERT INTO load_events(payload) VALUES (md5(random()::text));
   UPDATE load_events
     SET payload = md5(random()::text)
   WHERE id = (SELECT max(id) FROM load_events);
   SELECT count(*) FROM load_events WHERE id %% 10 = 0;'
)
FROM generate_series(1, ${ITERATIONS})\gexec
SQL

echo "query burst completed: ${ITERATIONS} iterations"
