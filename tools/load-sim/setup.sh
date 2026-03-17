#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=tools/load-sim/common.sh
source "${SCRIPT_DIR}/common.sh"

cat <<'SQL' | compose exec -T postgres psql -v ON_ERROR_STOP=1 -U postgres -d monitored_db
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

CREATE TABLE IF NOT EXISTS load_events (
    id BIGSERIAL PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS lock_test (
    id INTEGER PRIMARY KEY,
    v INTEGER NOT NULL
);

INSERT INTO lock_test(id, v)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;
SQL

echo "setup completed: extension/tables are ready in monitored_db"
