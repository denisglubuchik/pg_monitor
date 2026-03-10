from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pg_monitor.app import create_app
from pg_monitor.config import ApiSettings


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings()


@pytest.fixture
def app(settings: ApiSettings):
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)
