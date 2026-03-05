from __future__ import annotations

import logging
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from pg_monitor.logging import reset_request_id, set_request_id

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response

REQUEST_ID_HEADER = "X-Request-ID"
_logger = logging.getLogger("pg_monitor.api")


def register_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(
        request: Request, call_next
    ) -> Response:
        incoming = (request.headers.get(REQUEST_ID_HEADER) or "").strip()
        request_id = incoming or uuid4().hex
        request.state.request_id = request_id

        token = set_request_id(request_id)
        started_at = perf_counter()

        try:
            response = await call_next(request)
            duration_ms = int((perf_counter() - started_at) * 1000)
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
            response.headers[REQUEST_ID_HEADER] = request_id
            return response
        except Exception:
            duration_ms = int((perf_counter() - started_at) * 1000)
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
            raise
        finally:
            reset_request_id(token)
