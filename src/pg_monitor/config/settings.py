from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping, TypeVar, cast

from dotenv import dotenv_values
from pydantic import PostgresDsn, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

DOTENV_FILE_ENV = "PG_MONITOR_ENV_FILE"
DEFAULT_DOTENV_FILE = ".env"
DEFAULT_STORAGE_DSN = (
    "postgresql://postgres:postgres@localhost:5432/pg_monitor_storage"
)

ALLOWED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class ConfigurationError(ValueError):
    """Raised when settings cannot be resolved or validated."""


class _BaseMonitorSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PG_MONITOR_",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "pg-monitor"
    environment: str = "dev"
    log_level: str = "INFO"

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


class ApiSettings(_BaseMonitorSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    storage_dsn: PostgresDsn = DEFAULT_STORAGE_DSN


class CollectorSettings(_BaseMonitorSettings):
    collector_scheduler_enabled: bool = True
    runtime_poll_interval_seconds: int = 60
    query_poll_interval_seconds: int = 900
    collector_startup_retry_attempts: int = 5
    collector_startup_retry_base_delay_seconds: float = 1.0
    collector_startup_retry_max_delay_seconds: float = 10.0
    runtime_job_timeout_seconds: float = 30.0
    query_job_timeout_seconds: float = 60.0
    pg_dsn: PostgresDsn
    storage_dsn: PostgresDsn = DEFAULT_STORAGE_DSN

    @field_validator(
        "runtime_poll_interval_seconds",
        "query_poll_interval_seconds",
    )
    @classmethod
    def validate_poll_interval(cls, value: int) -> int:
        if value <= 0:
            msg = "poll interval must be greater than 0"
            raise ValueError(msg)
        return value

    @field_validator("collector_startup_retry_attempts")
    @classmethod
    def validate_retry_attempts(cls, value: int) -> int:
        if value <= 0:
            msg = "collector startup retry attempts must be greater than 0"
            raise ValueError(msg)
        return value

    @field_validator(
        "collector_startup_retry_base_delay_seconds",
        "collector_startup_retry_max_delay_seconds",
    )
    @classmethod
    def validate_retry_delay(cls, value: float) -> float:
        if value <= 0:
            msg = "collector startup retry delay must be greater than 0"
            raise ValueError(msg)
        return value

    @field_validator("runtime_job_timeout_seconds", "query_job_timeout_seconds")
    @classmethod
    def validate_job_timeout(cls, value: float) -> float:
        if value <= 0:
            msg = "collector job timeout must be greater than 0"
            raise ValueError(msg)
        return value


def resolve_settings_paths(
    environ: Mapping[str, str] | None = None,
) -> Path | None:
    env = os.environ if environ is None else environ
    return Path(env[DOTENV_FILE_ENV]) if DOTENV_FILE_ENV in env else None


TSettings = TypeVar("TSettings", bound=BaseSettings)


def _load_settings(
    settings_cls: type[TSettings],
    *,
    env_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> TSettings:
    env = os.environ if environ is None else environ
    resolved_env_path = resolve_settings_paths(env)
    dotenv_file = env_path or resolved_env_path or Path(DEFAULT_DOTENV_FILE)
    explicit_env_path = env_path is not None or DOTENV_FILE_ENV in env
    if explicit_env_path and not dotenv_file.exists():
        raise ConfigurationError(f".env file not found: {dotenv_file}")

    try:
        if environ is None:
            return settings_cls(
                _env_file=dotenv_file,
            )
        init_values = _build_settings_init_values(
            dotenv_file=dotenv_file,
            environ=environ,
        )
        return cast(
            "TSettings",
            _build_isolated_settings(settings_cls, init_values),
        )
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc


def load_api_settings(
    env_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> ApiSettings:
    return _load_settings(ApiSettings, env_path=env_path, environ=environ)


def load_collector_settings(
    env_path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> CollectorSettings:
    return _load_settings(CollectorSettings, env_path=env_path, environ=environ)


def _build_settings_init_values(
    *,
    dotenv_file: Path,
    environ: Mapping[str, str],
) -> dict[str, str]:
    env_prefix = "PG_MONITOR_"
    values: dict[str, str] = {}

    if dotenv_file.exists():
        dotenv_items = dotenv_values(dotenv_file)
        for key, value in dotenv_items.items():
            if key is None or value is None:
                continue
            upper_key = key.upper()
            if upper_key.startswith(env_prefix):
                field_name = upper_key[len(env_prefix) :].lower()
                values[field_name] = value

    for key, value in environ.items():
        upper_key = key.upper()
        if upper_key.startswith(env_prefix):
            field_name = upper_key[len(env_prefix) :].lower()
            values[field_name] = value

    return values


def _build_isolated_settings(
    settings_cls: type[TSettings],
    init_values: Mapping[str, str],
) -> TSettings:
    class IsolatedSettings(settings_cls):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls: type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
        ) -> tuple[PydanticBaseSettingsSource, ...]:
            del settings_cls
            del env_settings
            del dotenv_settings
            del file_secret_settings
            return (init_settings,)

    return IsolatedSettings(**init_values)
