from __future__ import annotations

from datetime import UTC, datetime

from pg_monitor.query_analytics import (
    PeriodTopQueriesResult,
    PeriodWindow,
    QueryAnalyticsService,
    QueryDelta,
    QuerySortBy,
    WeekOverWeekQueriesResult,
)


def _build_period_result(
    *,
    db_identifier: str,
    limit: int,
    sort_by: QuerySortBy,
    queryid: str,
) -> PeriodTopQueriesResult:
    start_at = datetime(2026, 3, 1, 0, 0, tzinfo=UTC)
    end_at = datetime(2026, 3, 8, 0, 0, tzinfo=UTC)
    return PeriodTopQueriesResult(
        db_identifier=db_identifier,
        window=PeriodWindow(start_at=start_at, end_at=end_at),
        snapshot_start_at=start_at,
        snapshot_end_at=end_at,
        sort_by=sort_by,
        limit=limit,
        items=[
            QueryDelta(
                queryid=queryid,
                dbid=1,
                userid=10,
                query="SELECT 1",
                calls_delta=12,
                total_exec_time_ms_delta=35.5,
                mean_exec_time_ms_delta=2.95,
                rows_delta=12,
                shared_blks_hit_delta=0,
                shared_blks_read_delta=0,
                shared_blks_dirtied_delta=0,
                shared_blks_written_delta=0,
            )
        ],
    )


def test_weekly_top_endpoint_returns_payload(client, monkeypatch) -> None:
    async def fake_weekly(
        self: QueryAnalyticsService,
        *,
        db_identifier: str,
        limit: int,
        sort_by: QuerySortBy,
        window_start_at: datetime | None = None,
        window_end_at: datetime | None = None,
        now: datetime | None = None,
    ) -> PeriodTopQueriesResult:
        del self, now, window_start_at, window_end_at
        return _build_period_result(
            db_identifier=db_identifier,
            limit=limit,
            sort_by=sort_by,
            queryid="q-weekly",
        )

    monkeypatch.setattr(
        QueryAnalyticsService,
        "get_weekly_top_queries",
        fake_weekly,
    )

    response = client.get(
        "/analytics/queries/weekly-top",
        params={
            "db_identifier": "postgres@127.0.0.1:5432",
            "limit": 5,
            "sort_by": "total_exec_time_ms_delta",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["db_identifier"] == "postgres@127.0.0.1:5432"
    assert payload["limit"] == 5
    assert payload["items"][0]["queryid"] == "q-weekly"


def test_week_over_week_endpoint_returns_payload(
    client,
    monkeypatch,
) -> None:
    async def fake_week_over_week(
        self: QueryAnalyticsService,
        *,
        db_identifier: str,
        limit: int,
        sort_by: QuerySortBy,
        window_start_at: datetime | None = None,
        window_end_at: datetime | None = None,
        now: datetime | None = None,
    ) -> WeekOverWeekQueriesResult:
        del self, now, window_start_at, window_end_at
        return WeekOverWeekQueriesResult(
            db_identifier=db_identifier,
            sort_by=sort_by,
            limit=limit,
            current_week=_build_period_result(
                db_identifier=db_identifier,
                limit=limit,
                sort_by=sort_by,
                queryid="q-current",
            ),
            previous_week=_build_period_result(
                db_identifier=db_identifier,
                limit=limit,
                sort_by=sort_by,
                queryid="q-previous",
            ),
        )

    monkeypatch.setattr(
        QueryAnalyticsService,
        "get_week_over_week_queries",
        fake_week_over_week,
    )

    response = client.get(
        "/analytics/queries/week-over-week",
        params={
            "db_identifier": "postgres@127.0.0.1:5432",
            "limit": 10,
            "sort_by": "calls_delta",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sort_by"] == "calls_delta"
    assert payload["current_week"]["items"][0]["queryid"] == "q-current"
    assert payload["previous_week"]["items"][0]["queryid"] == "q-previous"


def test_weekly_top_endpoint_requires_full_window_pair(client) -> None:
    response = client.get(
        "/analytics/queries/weekly-top",
        params={
            "db_identifier": "postgres@127.0.0.1:5432",
            "window_start_at": "2026-03-01T00:00:00Z",
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "window_start_at and window_end_at must be provided together"
    )
