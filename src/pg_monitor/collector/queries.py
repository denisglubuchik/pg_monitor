from __future__ import annotations

SQL_DB_IDENTIFIER = """
SELECT
    current_database() AS db_name,
    COALESCE(inet_server_addr()::text, 'local') AS host,
    COALESCE(inet_server_port(), 5432) AS port
"""

SQL_CHECK_PG_STAT_STATEMENTS = """
SELECT EXISTS (
    SELECT 1
    FROM pg_extension
    WHERE extname = 'pg_stat_statements'
) AS is_available
"""

SQL_PING = """
SELECT 1 AS ok
"""

SQL_RUNTIME_ACTIVITY = """
SELECT
    COUNT(*) FILTER (WHERE state = 'active')::bigint AS active_connections,
    COUNT(*) FILTER (
        WHERE wait_event_type = 'Lock'
    )::bigint AS blocked_sessions,
    MAX(EXTRACT(EPOCH FROM (now() - xact_start)))
        FILTER (WHERE xact_start IS NOT NULL) AS longest_tx_duration_s
FROM pg_stat_activity
WHERE pid <> pg_backend_pid()
"""

SQL_RUNTIME_LOCKS = """
SELECT
    COUNT(*) FILTER (WHERE NOT granted)::bigint AS waiting_locks,
    COUNT(*) FILTER (WHERE granted)::bigint AS granted_locks
FROM pg_locks
"""

SQL_RUNTIME_DATABASE = """
SELECT
    stats.datid,
    stats.datname,
    stats.numbackends,
    stats.xact_commit,
    stats.xact_rollback,
    stats.blks_read,
    stats.blks_hit,
    stats.deadlocks
FROM pg_stat_database AS stats
JOIN pg_database AS db ON db.oid = stats.datid
WHERE NOT db.datistemplate
ORDER BY stats.datname
"""

SQL_QUERY_STATEMENTS = """
SELECT
    queryid::text AS queryid,
    dbid,
    userid,
    query,
    calls,
    total_exec_time AS total_exec_time_ms,
    mean_exec_time AS mean_exec_time_ms,
    rows,
    shared_blks_hit,
    shared_blks_read,
    shared_blks_dirtied,
    shared_blks_written
FROM pg_stat_statements
WHERE queryid IS NOT NULL
  AND toplevel
  AND dbid = (
      SELECT oid
      FROM pg_database
      WHERE datname = current_database()
  )
"""
