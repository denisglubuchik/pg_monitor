from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from pg_monitor.api import register_api
from pg_monitor.config import Settings, load_settings, resolve_settings_paths
from pg_monitor.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or _load_runtime_settings()
    configure_logging(
        level=app_settings.log_level,
        service=app_settings.app_name,
        environment=app_settings.environment,
    )

    app = FastAPI(title=app_settings.app_name)
    app.state.settings = app_settings
    register_api(app)
    return app


def run() -> None:
    app_settings = _load_runtime_settings()
    app = create_app(app_settings)
    uvicorn.run(
        app,
        host=app_settings.host,
        port=app_settings.port,
        log_config=None,
    )


def _load_runtime_settings() -> Settings:
    env_path = resolve_settings_paths()
    return load_settings(env_path=env_path)
