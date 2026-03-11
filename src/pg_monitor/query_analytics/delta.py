from __future__ import annotations

from typing import TYPE_CHECKING

from .models import QueryDelta

if TYPE_CHECKING:
    from pg_monitor.storage import QuerySnapshotPoint, QuerySnapshotRow


def build_query_deltas(
    start_point: QuerySnapshotPoint | None,
    end_point: QuerySnapshotPoint | None,
) -> list[QueryDelta]:
    if end_point is None:
        return []

    start_rows = {} if start_point is None else _index_rows(start_point.rows)
    deltas: list[QueryDelta] = []

    for end_row in end_point.rows:
        key = _row_key(end_row)
        start_row = start_rows.get(key)

        calls_delta = end_row.calls - (start_row.calls if start_row else 0)
        total_exec_time_ms_delta = end_row.total_exec_time_ms - (
            start_row.total_exec_time_ms if start_row else 0.0
        )
        rows_delta = end_row.rows - (start_row.rows if start_row else 0)
        shared_blks_hit_delta = end_row.shared_blks_hit - (
            start_row.shared_blks_hit if start_row else 0
        )
        shared_blks_read_delta = end_row.shared_blks_read - (
            start_row.shared_blks_read if start_row else 0
        )
        shared_blks_dirtied_delta = end_row.shared_blks_dirtied - (
            start_row.shared_blks_dirtied if start_row else 0
        )
        shared_blks_written_delta = end_row.shared_blks_written - (
            start_row.shared_blks_written if start_row else 0
        )

        # Negative delta means counters were reset/restarted in the interval.
        if (
            calls_delta < 0
            or total_exec_time_ms_delta < 0
            or rows_delta < 0
            or shared_blks_hit_delta < 0
            or shared_blks_read_delta < 0
            or shared_blks_dirtied_delta < 0
            or shared_blks_written_delta < 0
        ):
            continue

        mean_exec_time_ms_delta = (
            total_exec_time_ms_delta / calls_delta if calls_delta > 0 else None
        )
        deltas.append(
            QueryDelta(
                queryid=end_row.queryid,
                dbid=end_row.dbid,
                userid=end_row.userid,
                query=end_row.query,
                calls_delta=calls_delta,
                total_exec_time_ms_delta=total_exec_time_ms_delta,
                mean_exec_time_ms_delta=mean_exec_time_ms_delta,
                rows_delta=rows_delta,
                shared_blks_hit_delta=shared_blks_hit_delta,
                shared_blks_read_delta=shared_blks_read_delta,
                shared_blks_dirtied_delta=shared_blks_dirtied_delta,
                shared_blks_written_delta=shared_blks_written_delta,
            )
        )

    return deltas


def _index_rows(
    rows: list[QuerySnapshotRow],
) -> dict[tuple[str, int, int], QuerySnapshotRow]:
    return {_row_key(row): row for row in rows}


def _row_key(row: QuerySnapshotRow) -> tuple[str, int, int]:
    return (row.queryid, row.dbid, row.userid)
