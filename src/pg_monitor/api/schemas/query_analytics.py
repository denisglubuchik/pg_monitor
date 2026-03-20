from __future__ import annotations

import datetime as dt  # noqa: TC003
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from pg_monitor.query_analytics import (
        PeriodTopQueriesResult,
        WeekOverWeekQueriesResult,
    )


class QuerySortByResponse(StrEnum):
    TOTAL_EXEC_TIME_MS = "total_exec_time_ms_delta"
    CALLS = "calls_delta"


class QueryDeltaResponse(BaseModel):
    queryid: str
    dbid: int
    userid: int
    query: str
    calls_delta: int
    total_exec_time_ms_delta: float
    mean_exec_time_ms_delta: float | None
    rows_delta: int
    shared_blks_hit_delta: int
    shared_blks_read_delta: int
    shared_blks_dirtied_delta: int
    shared_blks_written_delta: int


class PeriodTopQueriesResponse(BaseModel):
    db_identifier: str
    window_start_at: dt.datetime
    window_end_at: dt.datetime
    snapshot_start_at: dt.datetime | None
    snapshot_end_at: dt.datetime | None
    sort_by: QuerySortByResponse
    limit: int
    items: list[QueryDeltaResponse] = Field(default_factory=list)


class WeekOverWeekQueriesResponse(BaseModel):
    db_identifier: str
    sort_by: QuerySortByResponse
    limit: int
    current_week: PeriodTopQueriesResponse
    previous_week: PeriodTopQueriesResponse


def to_period_response(
    result: PeriodTopQueriesResult,
) -> PeriodTopQueriesResponse:
    return PeriodTopQueriesResponse(
        db_identifier=result.db_identifier,
        window_start_at=result.window.start_at,
        window_end_at=result.window.end_at,
        snapshot_start_at=result.snapshot_start_at,
        snapshot_end_at=result.snapshot_end_at,
        sort_by=QuerySortByResponse(result.sort_by.value),
        limit=result.limit,
        items=[
            QueryDeltaResponse(
                queryid=item.queryid,
                dbid=item.dbid,
                userid=item.userid,
                query=item.query,
                calls_delta=item.calls_delta,
                total_exec_time_ms_delta=item.total_exec_time_ms_delta,
                mean_exec_time_ms_delta=item.mean_exec_time_ms_delta,
                rows_delta=item.rows_delta,
                shared_blks_hit_delta=item.shared_blks_hit_delta,
                shared_blks_read_delta=item.shared_blks_read_delta,
                shared_blks_dirtied_delta=item.shared_blks_dirtied_delta,
                shared_blks_written_delta=item.shared_blks_written_delta,
            )
            for item in result.items
        ],
    )


def to_week_over_week_response(
    result: WeekOverWeekQueriesResult,
) -> WeekOverWeekQueriesResponse:
    return WeekOverWeekQueriesResponse(
        db_identifier=result.db_identifier,
        sort_by=QuerySortByResponse(result.sort_by.value),
        limit=result.limit,
        current_week=to_period_response(result.current_week),
        previous_week=to_period_response(result.previous_week),
    )
