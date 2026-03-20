from __future__ import annotations

import logging
from time import perf_counter
from uuid import uuid4

from pg_monitor.logging import reset_request_id, set_request_id
from pg_monitor.metrics import service_metrics

REQUEST_ID_HEADER = "X-Request-ID"
UNMATCHED_ROUTE_LABEL = "/__unmatched__"
_logger = logging.getLogger("pg_monitor.api")


def register_middlewares(app) -> None:
    @app.middleware("http")
    async def request_context_middleware(
        request, call_next
    ):
        incoming = (request.headers.get(REQUEST_ID_HEADER) or "").strip()
        request_id = incoming or uuid4().hex
        request.state.request_id = request_id

        token = set_request_id(request_id)
        started_at = perf_counter()

        try:
            response = await call_next(request)
            elapsed = perf_counter() - started_at
            duration_ms = int(elapsed * 1000)
            _logger.info(
                "http_request_completed",
                extra={
                    "component": "api",
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
            service_metrics.observe_http_request(
                method=request.method,
                path=_resolve_metrics_path(request),
                status_code=response.status_code,
                duration_seconds=elapsed,
            )
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            elapsed = perf_counter() - started_at
            duration_ms = int(elapsed * 1000)
            _logger.exception(
                "http_request_failed",
                extra={
                    "component": "api",
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error_type": "unhandled_exception",
                },
            )
            service_metrics.observe_http_request(
                method=request.method,
                path=_resolve_metrics_path(request),
                status_code=500,
                duration_seconds=elapsed,
            )
            raise
        finally:
            reset_request_id(token)


def _resolve_metrics_path(request) -> str:
    route = request.scope.get("route")
    if route is not None:
        route_path = getattr(route, "path", None)
        if route_path:
            return str(route_path)
    return UNMATCHED_ROUTE_LABEL
