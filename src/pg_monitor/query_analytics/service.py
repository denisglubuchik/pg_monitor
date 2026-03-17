from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol, Self

from .delta import build_query_deltas
from .models import (
    PeriodTopQueriesResult,
    PeriodWindow,
    QueryDelta,
    QuerySortBy,
    WeekOverWeekQueriesResult,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from pg_monitor.storage import QuerySnapshotPoint


class QuerySnapshotReader(Protocol):
    async def get_latest_snapshot_at_or_before(
        self,
        *,
        db_identifier: str,
        ts: datetime,
    ) -> QuerySnapshotPoint | None: ...


class QueryAnalyticsUnitOfWork(Protocol):
    query_snapshots: QuerySnapshotReader

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class QueryAnalyticsService:
    def __init__(
        self,
        uow_factory: Callable[[], QueryAnalyticsUnitOfWork],
    ) -> None:
        self._uow_factory = uow_factory

    async def get_weekly_top_queries(
        self,
        *,
        db_identifier: str,
        limit: int = 20,
        sort_by: QuerySortBy = QuerySortBy.TOTAL_EXEC_TIME_MS,
        window_start_at: datetime | None = None,
        window_end_at: datetime | None = None,
        now: datetime | None = None,
    ) -> PeriodTopQueriesResult:
        window = _resolve_current_window(
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            now=now,
        )
        return await self.get_period_top_queries(
            db_identifier=db_identifier,
            window=window,
            limit=limit,
            sort_by=sort_by,
        )

    async def get_week_over_week_queries(
        self,
        *,
        db_identifier: str,
        limit: int = 20,
        sort_by: QuerySortBy = QuerySortBy.TOTAL_EXEC_TIME_MS,
        window_start_at: datetime | None = None,
        window_end_at: datetime | None = None,
        now: datetime | None = None,
    ) -> WeekOverWeekQueriesResult:
        current_window = _resolve_current_window(
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            now=now,
        )
        current_start = current_window.start_at
        window_end = current_window.end_at
        duration = window_end - current_start
        previous_start = current_start - duration

        current_week = await self.get_period_top_queries(
            db_identifier=db_identifier,
            window=current_window,
            limit=limit,
            sort_by=sort_by,
        )
        previous_week = await self.get_period_top_queries(
            db_identifier=db_identifier,
            window=PeriodWindow(start_at=previous_start, end_at=current_start),
            limit=limit,
            sort_by=sort_by,
        )
        return WeekOverWeekQueriesResult(
            db_identifier=db_identifier,
            sort_by=sort_by,
            limit=limit,
            current_week=current_week,
            previous_week=previous_week,
        )

    async def get_period_top_queries(
        self,
        *,
        db_identifier: str,
        window: PeriodWindow,
        limit: int = 20,
        sort_by: QuerySortBy = QuerySortBy.TOTAL_EXEC_TIME_MS,
    ) -> PeriodTopQueriesResult:
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if not db_identifier:
            raise ValueError("db_identifier is required")

        async with self._uow_factory() as uow:
            start_point = (
                await uow.query_snapshots.get_latest_snapshot_at_or_before(
                    db_identifier=db_identifier,
                    ts=window.start_at,
                )
            )
            end_point = (
                await uow.query_snapshots.get_latest_snapshot_at_or_before(
                    db_identifier=db_identifier,
                    ts=window.end_at,
                )
            )

        deltas = build_query_deltas(start_point, end_point)
        sorted_deltas = _sort_deltas(deltas, sort_by=sort_by)
        limited = sorted_deltas[:limit]

        return PeriodTopQueriesResult(
            db_identifier=db_identifier,
            window=window,
            snapshot_start_at=None
            if start_point is None
            else start_point.captured_at,
            snapshot_end_at=None
            if end_point is None
            else end_point.captured_at,
            sort_by=sort_by,
            limit=limit,
            items=limited,
        )


def _sort_deltas(
    deltas: list[QueryDelta],
    *,
    sort_by: QuerySortBy,
) -> list[QueryDelta]:
    if sort_by == QuerySortBy.CALLS:
        return sorted(
            deltas,
            key=lambda item: (
                item.calls_delta,
                item.total_exec_time_ms_delta,
            ),
            reverse=True,
        )
    return sorted(
        deltas,
        key=lambda item: (
            item.total_exec_time_ms_delta,
            item.calls_delta,
        ),
        reverse=True,
    )


def _resolve_current_window(
    *,
    window_start_at: datetime | None,
    window_end_at: datetime | None,
    now: datetime | None,
) -> PeriodWindow:
    if (window_start_at is None) != (window_end_at is None):
        raise ValueError(
            "window_start_at and window_end_at must be provided together"
        )

    if window_start_at is not None and window_end_at is not None:
        return PeriodWindow(start_at=window_start_at, end_at=window_end_at)

    resolved_end = now or datetime.now(UTC)
    resolved_start = resolved_end - timedelta(days=7)
    return PeriodWindow(start_at=resolved_start, end_at=resolved_end)
