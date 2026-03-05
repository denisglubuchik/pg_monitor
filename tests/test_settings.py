from __future__ import annotations

import pytest

from pg_monitor.config import ConfigurationError, load_settings


def test_settings_priority_defaults_dotenv_env(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        (
            "PG_MONITOR_APP_NAME=from-dotenv-app\n"
            "PG_MONITOR_ENVIRONMENT=staging\n"
            "PG_MONITOR_HOST=127.0.0.1\n"
            "PG_MONITOR_PORT=9200\n"
            "PG_MONITOR_LOG_LEVEL=warning\n"
            "PG_MONITOR_PG_DSN="
            "postgresql://dotenv_user:dotenv_password@localhost:5432/dotenv_db\n"
        ),
        encoding="utf-8",
    )

    settings = load_settings(
        env_path=env_file,
        environ={
            "PG_MONITOR_APP_NAME": "from-env-app",
            "PG_MONITOR_PORT": "9300",
            "PG_MONITOR_LOG_LEVEL": "ERROR",
            "PG_MONITOR_PG_DSN": "postgresql://env_user:env_password@localhost:5432/env_db",
        },
    )

    assert settings.app_name == "from-env-app"
    assert settings.environment == "staging"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9300
    assert settings.log_level == "ERROR"
    assert "env_db" in str(settings.pg_dsn)


def test_settings_require_pg_dsn(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ConfigurationError, match="pg_dsn"):
        load_settings(environ={})


def test_settings_fail_on_explicit_missing_env_file() -> None:
    with pytest.raises(ConfigurationError, match=".env file not found"):
        load_settings(environ={"PG_MONITOR_ENV_FILE": "/tmp/not-found.env"})
