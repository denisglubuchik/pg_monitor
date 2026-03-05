from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pg_monitor.app import create_app
from pg_monitor.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(pg_dsn="postgresql://user:password@localhost:5432/monitoring")


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)
