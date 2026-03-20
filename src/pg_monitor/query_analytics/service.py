from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Protocol, Self

from .delta import build_query_deltas
from .errors import QueryAnalyticsValidationError
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
        _validate_period_request(db_identifier=db_identifier, limit=limit)
        current_window = _resolve_current_window(
            window_start_at=window_start_at,
            window_end_at=window_end_at,
            now=now,
        )
        current_start = current_window.start_at
        window_end = current_window.end_at
        duration = window_end - current_start
        previous_start = current_start - duration
        previous_window = PeriodWindow(
            start_at=previous_start,
            end_at=current_start,
        )

        points = await self._load_snapshot_points(
            db_identifier=db_identifier,
            timestamps=[
                previous_window.start_at,
                previous_window.end_at,
                current_window.end_at,
            ],
        )
        previous_start_point = points[previous_window.start_at]
        boundary_point = points[previous_window.end_at]
        current_end_point = points[current_window.end_at]

        current_week = _build_period_result(
            db_identifier=db_identifier,
            window=current_window,
            start_point=boundary_point,
            end_point=current_end_point,
            limit=limit,
            sort_by=sort_by,
        )
        previous_week = _build_period_result(
            db_identifier=db_identifier,
            window=previous_window,
            start_point=previous_start_point,
            end_point=boundary_point,
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
        _validate_period_request(db_identifier=db_identifier, limit=limit)
        points = await self._load_snapshot_points(
            db_identifier=db_identifier,
            timestamps=[window.start_at, window.end_at],
        )
        return _build_period_result(
            db_identifier=db_identifier,
            window=window,
            start_point=points[window.start_at],
            end_point=points[window.end_at],
            limit=limit,
            sort_by=sort_by,
        )

    async def _load_snapshot_points(
        self,
        *,
        db_identifier: str,
        timestamps: list[datetime],
    ) -> dict[datetime, QuerySnapshotPoint | None]:
        ordered_unique = list(dict.fromkeys(timestamps))
        async with self._uow_factory() as uow:
            reader = uow.query_snapshots
            bulk_loader = getattr(
                reader,
                "get_latest_snapshots_at_or_before",
                None,
            )
            if callable(bulk_loader):
                loaded = await bulk_loader(
                    db_identifier=db_identifier,
                    timestamps=ordered_unique,
                )
                return {ts: loaded.get(ts) for ts in ordered_unique}

            points: dict[datetime, QuerySnapshotPoint | None] = {}
            for ts in ordered_unique:
                points[ts] = (
                    await reader.get_latest_snapshot_at_or_before(
                        db_identifier=db_identifier,
                        ts=ts,
                    )
                )
            return points


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
        raise QueryAnalyticsValidationError(
            "window_start_at and window_end_at must be provided together"
        )

    if window_start_at is not None and window_end_at is not None:
        return PeriodWindow(start_at=window_start_at, end_at=window_end_at)

    resolved_end = now or datetime.now(UTC)
    resolved_start = resolved_end - timedelta(days=7)
    return PeriodWindow(start_at=resolved_start, end_at=resolved_end)


def _validate_period_request(*, db_identifier: str, limit: int) -> None:
    if limit <= 0:
        raise QueryAnalyticsValidationError("limit must be greater than 0")
    if not db_identifier:
        raise QueryAnalyticsValidationError("db_identifier is required")


def _build_period_result(
    *,
    db_identifier: str,
    window: PeriodWindow,
    start_point: QuerySnapshotPoint | None,
    end_point: QuerySnapshotPoint | None,
    limit: int,
    sort_by: QuerySortBy,
) -> PeriodTopQueriesResult:
    deltas = build_query_deltas(start_point, end_point)
    sorted_deltas = _sort_deltas(deltas, sort_by=sort_by)
    limited = sorted_deltas[:limit]

    return PeriodTopQueriesResult(
        db_identifier=db_identifier,
        window=window,
        snapshot_start_at=(
            None if start_point is None else start_point.captured_at
        ),
        snapshot_end_at=None if end_point is None else end_point.captured_at,
        sort_by=sort_by,
        limit=limit,
        items=limited,
    )
