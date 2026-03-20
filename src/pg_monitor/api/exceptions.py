from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from pg_monitor.query_analytics.errors import QueryAnalyticsValidationError
from pg_monitor.storage import StorageError

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

logger = logging.getLogger("pg_monitor.api.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(QueryAnalyticsValidationError)
    async def handle_query_analytics_validation_error(
        request: Request,
        exc: QueryAnalyticsValidationError,
    ) -> JSONResponse:
        logger.warning(
            "query_analytics_validation_error",
            extra={
                "component": "api",
                "method": request.method,
                "path": request.url.path,
                "error_type": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(StorageError)
    async def handle_storage_error(
        request: Request,
        exc: StorageError,
    ) -> JSONResponse:
        logger.warning(
            "storage_error",
            extra={
                "component": "api",
                "method": request.method,
                "path": request.url.path,
                "error_type": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=503,
            content={"detail": "storage is unavailable"},
        )
