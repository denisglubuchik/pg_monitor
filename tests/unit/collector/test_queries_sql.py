from __future__ import annotations

from pg_monitor.collector.queries import SQL_QUERY_STATEMENTS


def test_sql_query_statements_filters_current_database() -> None:
    normalized = " ".join(SQL_QUERY_STATEMENTS.split()).lower()
    expected_fragment = (
        "dbid = ( select oid from pg_database where "
        "datname = current_database() )"
    )
    assert expected_fragment in normalized
