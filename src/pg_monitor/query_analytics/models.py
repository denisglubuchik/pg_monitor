from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class QuerySortBy(StrEnum):
    TOTAL_EXEC_TIME_MS = "total_exec_time_ms_delta"
    CALLS = "calls_delta"


@dataclass(frozen=True, slots=True)
class PeriodWindow:
    start_at: datetime
    end_at: datetime

    def __post_init__(self) -> None:
        if self.start_at >= self.end_at:
            raise ValueError("period window start_at must be before end_at")


@dataclass(frozen=True, slots=True)
class QueryDelta:
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


@dataclass(frozen=True, slots=True)
class PeriodTopQueriesResult:
    db_identifier: str
    window: PeriodWindow
    snapshot_start_at: datetime | None
    snapshot_end_at: datetime | None
    sort_by: QuerySortBy
    limit: int
    items: list[QueryDelta]


@dataclass(frozen=True, slots=True)
class WeekOverWeekQueriesResult:
    db_identifier: str
    sort_by: QuerySortBy
    limit: int
    current_week: PeriodTopQueriesResult
    previous_week: PeriodTopQueriesResult
