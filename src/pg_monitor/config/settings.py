from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Mapping

from pydantic import PostgresDsn, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

DOTENV_FILE_ENV = "PG_MONITOR_ENV_FILE"
DEFAULT_DOTENV_FILE = ".env"

ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class ConfigurationError(ValueError):
    """Raised when settings cannot be resolved or validated."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PG_MONITOR_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "pg-monitor"
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    pg_dsn: PostgresDsn

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            dotenv_settings,
            init_settings,
            file_secret_settings,
        )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in ALLOWED_LOG_LEVELS:
            allowed = ", ".join(sorted(ALLOWED_LOG_LEVELS))
            msg = f"unsupported log level: {value}. Allowed: {allowed}"
            raise ValueError(msg)
        return normalized


def resolve_settings_paths(
    environ: Mapping[str, str] | None = None,
) -> Path | None:
    env = os.environ if environ is None else environ
    return Path(env[DOTENV_FILE_ENV]) if DOTENV_FILE_ENV in env else None


def load_settings(
    env_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    env = os.environ if environ is None else environ
    resolved_env_path = resolve_settings_paths(env)
    dotenv_file = env_path or resolved_env_path or Path(DEFAULT_DOTENV_FILE)
    explicit_env_path = env_path is not None or DOTENV_FILE_ENV in env
    if explicit_env_path and not dotenv_file.exists():
        raise ConfigurationError(f".env file not found: {dotenv_file}")

    try:
        with _override_environ(environ):
            return Settings(
                _env_file=dotenv_file,
            )
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc


@contextmanager
def _override_environ(environ: Mapping[str, str] | None) -> Iterator[None]:
    if environ is None:
        yield
        return

    previous = os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(environ)
        yield
    finally:
        os.environ.clear()
        os.environ.update(previous)
