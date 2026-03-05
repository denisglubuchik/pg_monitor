from fastapi import FastAPI

from .health import router as health_router
from .middleware import REQUEST_ID_HEADER, register_middlewares


def register_routers(app: FastAPI) -> None:
    app.include_router(health_router)


def register_api(app: FastAPI) -> None:
    register_middlewares(app)
    register_routers(app)


__all__ = [
    "health_router",
    "register_routers",
    "register_middlewares",
    "register_api",
    "REQUEST_ID_HEADER",
]
