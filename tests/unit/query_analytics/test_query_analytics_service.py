from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Self

import pytest

from pg_monitor.query_analytics import (
    PeriodWindow,
    QueryAnalyticsService,
    QuerySortBy,
)
from pg_monitor.storage import QuerySnapshotPoint, QuerySnapshotRow


class FakeQuerySnapshotRepository:
    def __init__(
        self,
        points: dict[datetime, QuerySnapshotPoint | None],
    ) -> None:
        self._points = points
        self.bulk_calls: list[list[datetime]] = []

    async def get_latest_snapshot_at_or_before(
        self,
        *,
        db_identifier: str,
        ts: datetime,
    ) -> QuerySnapshotPoint | None:
        del db_identifier
        return self._points.get(ts)

    async def get_latest_snapshots_at_or_before(
        self,
        *,
        db_identifier: str,
        timestamps: list[datetime],
    ) -> dict[datetime, QuerySnapshotPoint | None]:
        del db_identifier
        self.bulk_calls.append(timestamps)
        return {ts: self._points.get(ts) for ts in timestamps}


class FakeUnitOfWork:
    def __init__(self, repository: FakeQuerySnapshotRepository) -> None:
        self.query_snapshots = repository

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


class FakeUnitOfWorkFactory:
    def __init__(self, repository: FakeQuerySnapshotRepository) -> None:
        self._repository = repository

    def __call__(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self._repository)


def _make_row(
    *,
    captured_at: datetime,
    queryid: str,
    calls: int,
    total_exec_time_ms: float,
) -> QuerySnapshotRow:
    return QuerySnapshotRow(
        captured_at=captured_at,
        db_identifier="postgres@127.0.0.1:5432",
        queryid=queryid,
        dbid=1,
        userid=10,
        query=f"SELECT {queryid}",
        calls=calls,
        total_exec_time_ms=total_exec_time_ms,
        mean_exec_time_ms=0.0,
        rows=calls,
        shared_blks_hit=0,
        shared_blks_read=0,
        shared_blks_dirtied=0,
        shared_blks_written=0,
    )


def test_period_top_queries_sorted_by_total_exec_time() -> None:
    start_at = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 3, 8, 0, 0, tzinfo=UTC)

    start_point = QuerySnapshotPoint(
        captured_at=start_at,
        rows=[
            _make_row(
                captured_at=start_at,
                queryid="q1",
                calls=10,
                total_exec_time_ms=100.0,
            ),
            _make_row(
                captured_at=start_at,
                queryid="q2",
                calls=20,
                total_exec_time_ms=90.0,
            ),
        ],
    )
    end_point = QuerySnapshotPoint(
        captured_at=end_at,
        rows=[
            _make_row(
                captured_at=end_at,
                queryid="q1",
                calls=15,
                total_exec_time_ms=180.0,
            ),
            _make_row(
                captured_at=end_at,
                queryid="q2",
                calls=5,
                total_exec_time_ms=40.0,
            ),
            _make_row(
                captured_at=end_at,
                queryid="q3",
                calls=4,
                total_exec_time_ms=30.0,
            ),
        ],
    )

    repo = FakeQuerySnapshotRepository(
        {
            start_at: start_point,
            end_at: end_point,
        }
    )
    service = QueryAnalyticsService(FakeUnitOfWorkFactory(repo))

    result = asyncio.run(
        service.get_period_top_queries(
            db_identifier="postgres@127.0.0.1:5432",
            window=PeriodWindow(start_at=start_at, end_at=end_at),
            limit=10,
            sort_by=QuerySortBy.TOTAL_EXEC_TIME_MS,
        )
    )

    # q2 is excluded because counters decreased (reset/restart case).
    assert [item.queryid for item in result.items] == ["q1", "q3"]
    assert result.items[0].total_exec_time_ms_delta == 80.0
    assert result.items[1].total_exec_time_ms_delta == 30.0


def test_period_top_queries_sorted_by_calls() -> None:
    start_at = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 3, 8, 0, 0, tzinfo=UTC)

    start_point = QuerySnapshotPoint(
        captured_at=start_at,
        rows=[
            _make_row(
                captured_at=start_at,
                queryid="q1",
                calls=1,
                total_exec_time_ms=10.0,
            ),
            _make_row(
                captured_at=start_at,
                queryid="q2",
                calls=1,
                total_exec_time_ms=10.0,
            ),
        ],
    )
    end_point = QuerySnapshotPoint(
        captured_at=end_at,
        rows=[
            _make_row(
                captured_at=end_at,
                queryid="q1",
                calls=11,
                total_exec_time_ms=20.0,
            ),
            _make_row(
                captured_at=end_at,
                queryid="q2",
                calls=5,
                total_exec_time_ms=200.0,
            ),
        ],
    )

    repo = FakeQuerySnapshotRepository(
        {
            start_at: start_point,
            end_at: end_point,
        }
    )
    service = QueryAnalyticsService(FakeUnitOfWorkFactory(repo))

    result = asyncio.run(
        service.get_period_top_queries(
            db_identifier="postgres@127.0.0.1:5432",
            window=PeriodWindow(start_at=start_at, end_at=end_at),
            limit=1,
            sort_by=QuerySortBy.CALLS,
        )
    )

    assert len(result.items) == 1
    assert result.items[0].queryid == "q1"
    assert result.items[0].calls_delta == 10


def test_weekly_top_queries_accepts_custom_window() -> None:
    start_at = datetime(2026, 3, 2, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 3, 5, 0, 0, tzinfo=UTC)

    start_point = QuerySnapshotPoint(
        captured_at=start_at,
        rows=[
            _make_row(
                captured_at=start_at,
                queryid="q1",
                calls=2,
                total_exec_time_ms=20.0,
            )
        ],
    )
    end_point = QuerySnapshotPoint(
        captured_at=end_at,
        rows=[
            _make_row(
                captured_at=end_at,
                queryid="q1",
                calls=5,
                total_exec_time_ms=80.0,
            )
        ],
    )

    repo = FakeQuerySnapshotRepository(
        {
            start_at: start_point,
            end_at: end_point,
        }
    )
    service = QueryAnalyticsService(FakeUnitOfWorkFactory(repo))

    result = asyncio.run(
        service.get_weekly_top_queries(
            db_identifier="postgres@127.0.0.1:5432",
            limit=10,
            sort_by=QuerySortBy.TOTAL_EXEC_TIME_MS,
            window_start_at=start_at,
            window_end_at=end_at,
        )
    )

    assert result.window.start_at == start_at
    assert result.window.end_at == end_at
    assert result.items[0].queryid == "q1"
    assert result.items[0].calls_delta == 3


def test_weekly_top_queries_requires_full_window_pair() -> None:
    service = QueryAnalyticsService(
        FakeUnitOfWorkFactory(FakeQuerySnapshotRepository({}))
    )

    with pytest.raises(
        ValueError,
        match="window_start_at and window_end_at must be provided together",
    ):
        asyncio.run(
            service.get_weekly_top_queries(
                db_identifier="postgres@127.0.0.1:5432",
                window_start_at=datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
            )
        )


def test_period_top_queries_skips_zero_delta_rows() -> None:
    start_at = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 3, 8, 0, 0, tzinfo=UTC)
    same_point = QuerySnapshotPoint(
        captured_at=end_at,
        rows=[
            _make_row(
                captured_at=end_at,
                queryid="q1",
                calls=10,
                total_exec_time_ms=100.0,
            )
        ],
    )
    repo = FakeQuerySnapshotRepository(
        {
            start_at: same_point,
            end_at: same_point,
        }
    )
    service = QueryAnalyticsService(FakeUnitOfWorkFactory(repo))

    result = asyncio.run(
        service.get_period_top_queries(
            db_identifier="postgres@127.0.0.1:5432",
            window=PeriodWindow(start_at=start_at, end_at=end_at),
        )
    )

    assert result.items == []


def test_week_over_week_uses_previous_window_of_same_length() -> None:
    current_start = datetime(2026, 3, 8, 0, 0, tzinfo=UTC)
    current_end = datetime(2026, 3, 15, 0, 0, tzinfo=UTC)
    previous_start = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    previous_end = current_start

    previous_point = QuerySnapshotPoint(
        captured_at=previous_end,
        rows=[
            _make_row(
                captured_at=previous_end,
                queryid="q-prev",
                calls=7,
                total_exec_time_ms=70.0,
            )
        ],
    )
    current_point = QuerySnapshotPoint(
        captured_at=current_end,
        rows=[
            _make_row(
                captured_at=current_end,
                queryid="q-current",
                calls=9,
                total_exec_time_ms=90.0,
            )
        ],
    )

    repo = FakeQuerySnapshotRepository(
        {
            previous_start: None,
            previous_end: previous_point,
            current_start: previous_point,
            current_end: current_point,
        }
    )
    service = QueryAnalyticsService(FakeUnitOfWorkFactory(repo))

    result = asyncio.run(
        service.get_week_over_week_queries(
            db_identifier="postgres@127.0.0.1:5432",
            window_start_at=current_start,
            window_end_at=current_end,
            sort_by=QuerySortBy.CALLS,
            limit=10,
        )
    )

    assert result.current_week.window.start_at == current_start
    assert result.current_week.window.end_at == current_end
    assert result.previous_week.window.start_at == previous_start
    assert result.previous_week.window.end_at == previous_end
    assert len(repo.bulk_calls) == 1
    assert repo.bulk_calls[0] == [previous_start, previous_end, current_end]


def test_weekly_top_queries_rejects_naive_window_datetime() -> None:
    service = QueryAnalyticsService(
        FakeUnitOfWorkFactory(FakeQuerySnapshotRepository({}))
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        asyncio.run(
            service.get_weekly_top_queries(
                db_identifier="postgres@127.0.0.1:5432",
                window_start_at=datetime(2026, 3, 1, 0, 0),
                window_end_at=datetime(2026, 3, 2, 0, 0),
            )
        )
