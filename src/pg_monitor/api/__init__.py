from fastapi import FastAPI

from .exceptions import register_exception_handlers
from .health import router as health_router
from .metrics import router as metrics_router
from .middleware import REQUEST_ID_HEADER, register_middlewares
from .query_analytics import router as query_analytics_router


def register_routers(app: FastAPI) -> None:
    app.include_router(health_router)
    app.include_router(metrics_router)
    app.include_router(query_analytics_router)


def register_api(app: FastAPI) -> None:
    register_exception_handlers(app)
    register_middlewares(app)
    register_routers(app)


__all__ = [
    "health_router",
    "register_routers",
    "register_middlewares",
    "register_exception_handlers",
    "register_api",
    "REQUEST_ID_HEADER",
    "query_analytics_router",
    "metrics_router",
]
