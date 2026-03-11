from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from dishka import make_async_container
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI

from pg_monitor.api import register_api
from pg_monitor.config import (
    ApiSettings,
    load_api_settings,
    resolve_settings_paths,
)
from pg_monitor.logging import configure_logging
from pg_monitor.providers import AppProvider

logger = logging.getLogger("pg_monitor.di")


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    app_settings = settings or _load_runtime_settings()
    configure_logging(
        level=app_settings.log_level,
        service=app_settings.app_name,
        environment=app_settings.environment,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        dishka_container = getattr(app.state, "dishka_container", None)
        if dishka_container is not None:
            await dishka_container.close()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.settings = app_settings

    container = make_async_container(
        AppProvider(app_settings),
        FastapiProvider(),
    )
    app.state.dishka_container = container
    setup_dishka(container=container, app=app)
    logger.info(
        "dishka_di_enabled",
        extra={"component": "api"},
    )

    register_api(app)
    return app

def _load_runtime_settings() -> ApiSettings:
    env_path = resolve_settings_paths()
    return load_api_settings(env_path=env_path)
