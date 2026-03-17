from __future__ import annotations

from pg_monitor.providers.collector import _build_db_identifier


def test_build_db_identifier_uses_stable_dsn_host() -> None:
    dsn = "postgresql://user:pass@postgres:5432/monitored_db"

    assert _build_db_identifier(dsn) == "monitored_db@postgres:5432"


def test_build_db_identifier_defaults_when_parts_missing() -> None:
    dsn = "postgresql:///monitored_db"

    assert _build_db_identifier(dsn) == "monitored_db@unknown:5432"
