from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query

from pg_monitor.api.schemas import (
    PeriodTopQueriesResponse,
    WeekOverWeekQueriesResponse,
    to_period_response,
    to_week_over_week_response,
)
from pg_monitor.query_analytics import QueryAnalyticsService, QuerySortBy

router = APIRouter(
    prefix="/analytics/queries",
    tags=["query-analytics"],
    route_class=DishkaRoute,
)


@router.get("/weekly-top", response_model=PeriodTopQueriesResponse)
async def get_weekly_top_queries(
    service: FromDishka[QueryAnalyticsService],
    db_identifier: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    sort_by: QuerySortBy = Query(default=QuerySortBy.TOTAL_EXEC_TIME_MS),
) -> PeriodTopQueriesResponse:
    result = await service.get_weekly_top_queries(
        db_identifier=db_identifier,
        limit=limit,
        sort_by=sort_by,
    )
    return to_period_response(result)


@router.get("/week-over-week", response_model=WeekOverWeekQueriesResponse)
async def get_week_over_week_queries(
    service: FromDishka[QueryAnalyticsService],
    db_identifier: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    sort_by: QuerySortBy = Query(default=QuerySortBy.TOTAL_EXEC_TIME_MS),
) -> WeekOverWeekQueriesResponse:
    result = await service.get_week_over_week_queries(
        db_identifier=db_identifier,
        limit=limit,
        sort_by=sort_by,
    )
    return to_week_over_week_response(result)
