from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from pg_monitor.app import create_app
from pg_monitor.config import ApiSettings


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="run integration tests (requires external services like Docker)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if config.getoption("--run-integration"):
        return

    skip_integration = pytest.mark.skip(
        reason="integration tests are disabled (use --run-integration)",
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings()


@pytest.fixture
def app(settings: ApiSettings):
    application = create_app(settings)
    try:
        yield application
    finally:
        asyncio.run(application.state.dishka_container.close())


class SyncAsgiClient:
    def __init__(self, app: Any) -> None:
        self.app = app
        self._base_url = "http://testserver"

    def get(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        async def _request() -> httpx.Response:
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url=self._base_url,
            ) as client:
                return await client.get(
                    url,
                    params=params,
                    headers=headers,
                )

        return asyncio.run(_request())


@pytest.fixture
def client(app):
    return SyncAsgiClient(app)
