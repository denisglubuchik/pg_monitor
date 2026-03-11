from __future__ import annotations

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response

from pg_monitor.metrics import (
    CONTENT_TYPE_LATEST,
    RuntimeMetricsExporter,
    RuntimeMetricsService,
)

router = APIRouter(tags=["metrics"], route_class=DishkaRoute)


@router.get("/metrics")
async def get_metrics(
    service: FromDishka[RuntimeMetricsService],
    exporter: FromDishka[RuntimeMetricsExporter],
    db_identifier: str | None = Query(default=None, min_length=1),
) -> Response:
    states = await service.get_metrics_state(db_identifier=db_identifier)
    payload = exporter.render(states=states, observed_at=service.current_time())
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
