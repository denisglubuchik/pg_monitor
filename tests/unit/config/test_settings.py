from __future__ import annotations

import pytest

from pg_monitor.config import (
    ApiSettings,
    CollectorSettings,
    ConfigurationError,
    load_api_settings,
    load_collector_settings,
)


def test_api_settings_priority_defaults_dotenv_env(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        (
            "PG_MONITOR_APP_NAME=from-dotenv-app\n"
            "PG_MONITOR_ENVIRONMENT=staging\n"
            "PG_MONITOR_HOST=127.0.0.1\n"
            "PG_MONITOR_PORT=9200\n"
            "PG_MONITOR_LOG_LEVEL=warning\n"
            "PG_MONITOR_STORAGE_DSN="
            "postgresql://dotenv_user:dotenv_password@localhost:5432/storage_dotenv\n"
        ),
        encoding="utf-8",
    )

    settings = load_api_settings(
        env_path=env_file,
        environ={
            "PG_MONITOR_APP_NAME": "from-env-app",
            "PG_MONITOR_PORT": "9300",
            "PG_MONITOR_LOG_LEVEL": "ERROR",
            "PG_MONITOR_STORAGE_DSN": "postgresql://env_user:env_password@localhost:5432/storage_env",
        },
    )

    assert isinstance(settings, ApiSettings)
    assert settings.app_name == "from-env-app"
    assert settings.environment == "staging"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9300
    assert settings.log_level == "ERROR"
    assert "storage_env" in str(settings.storage_dsn)


def test_collector_settings_priority_defaults_dotenv_env(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        (
            "PG_MONITOR_APP_NAME=collector-dotenv\n"
            "PG_MONITOR_COLLECTOR_SCHEDULER_ENABLED=false\n"
            "PG_MONITOR_RUNTIME_POLL_INTERVAL_SECONDS=120\n"
            "PG_MONITOR_QUERY_POLL_INTERVAL_SECONDS=1800\n"
            "PG_MONITOR_COLLECTOR_STARTUP_RETRY_ATTEMPTS=8\n"
            "PG_MONITOR_COLLECTOR_STARTUP_RETRY_BASE_DELAY_SECONDS=2\n"
            "PG_MONITOR_COLLECTOR_STARTUP_RETRY_MAX_DELAY_SECONDS=20\n"
            "PG_MONITOR_PG_DSN="
            "postgresql://dotenv_user:dotenv_password@localhost:5432/dotenv_db\n"
            "PG_MONITOR_STORAGE_DSN="
            "postgresql://dotenv_user:dotenv_password@localhost:5432/storage_dotenv\n"
        ),
        encoding="utf-8",
    )

    settings = load_collector_settings(
        env_path=env_file,
        environ={
            "PG_MONITOR_COLLECTOR_SCHEDULER_ENABLED": "true",
            "PG_MONITOR_RUNTIME_POLL_INTERVAL_SECONDS": "60",
            "PG_MONITOR_PG_DSN": "postgresql://env_user:env_password@localhost:5432/env_db",
            "PG_MONITOR_STORAGE_DSN": "postgresql://env_user:env_password@localhost:5432/storage_env",
        },
    )

    assert isinstance(settings, CollectorSettings)
    assert settings.app_name == "collector-dotenv"
    assert settings.collector_scheduler_enabled is True
    assert settings.runtime_poll_interval_seconds == 60
    assert settings.query_poll_interval_seconds == 1800
    assert settings.collector_startup_retry_attempts == 8
    assert settings.collector_startup_retry_base_delay_seconds == 2
    assert settings.collector_startup_retry_max_delay_seconds == 20
    assert "env_db" in str(settings.pg_dsn)
    assert "storage_env" in str(settings.storage_dsn)


def test_collector_settings_require_pg_dsn(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigurationError, match="pg_dsn"):
        load_collector_settings(environ={})


def test_settings_fail_on_explicit_missing_env_file() -> None:
    with pytest.raises(ConfigurationError, match=".env file not found"):
        load_api_settings(environ={"PG_MONITOR_ENV_FILE": "/tmp/not-found.env"})


def test_collector_settings_reject_non_positive_poll_interval(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        (
            "PG_MONITOR_PG_DSN=postgresql://dotenv_user:dotenv_password@localhost:5432/dotenv_db\n"
            "PG_MONITOR_RUNTIME_POLL_INTERVAL_SECONDS=0\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError, match="runtime_poll_interval_seconds"
    ):
        load_collector_settings(env_path=env_file, environ={})


def test_collector_settings_reject_non_positive_retry_attempts(
    tmp_path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        (
            "PG_MONITOR_PG_DSN=postgresql://dotenv_user:dotenv_password@localhost:5432/dotenv_db\n"
            "PG_MONITOR_COLLECTOR_STARTUP_RETRY_ATTEMPTS=0\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ConfigurationError, match="collector_startup_retry_attempts"
    ):
        load_collector_settings(env_path=env_file, environ={})
