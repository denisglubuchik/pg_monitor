from __future__ import annotations

import asyncio

import httpx

from pg_monitor.app import create_app
from pg_monitor.collector import CollectorConnectionError
from pg_monitor.collector.worker import run_worker
from pg_monitor.config import ApiSettings, CollectorSettings


def _get(app, path: str) -> httpx.Response:
    async def _request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    return asyncio.run(_request())


def test_app_has_no_embedded_collector_scheduler() -> None:
    app = create_app(ApiSettings())

    try:
        response = _get(app, "/healthz")
        assert response.status_code == 200
        assert not hasattr(app.state, "collector_scheduler")
    finally:
        asyncio.run(app.state.dishka_container.close())


def test_worker_starts_and_stops_scheduler(monkeypatch) -> None:
    events: list[str] = []

    class DummyScheduler:
        async def start(self) -> None:
            events.append("start")

        async def shutdown(self) -> None:
            events.append("shutdown")

    class DummyContainer:
        async def get(self, _dependency):
            return DummyScheduler()

        async def close(self) -> None:
            return None

    monkeypatch.setattr(
        "pg_monitor.collector.worker.make_async_container",
        lambda _provider: DummyContainer(),
    )

    stop_event = asyncio.Event()
    stop_event.set()

    asyncio.run(
        run_worker(
            settings=CollectorSettings(
                pg_dsn="postgresql://user:password@localhost:5432/monitoring",
                collector_scheduler_enabled=True,
            ),
            stop_event=stop_event,
        )
    )

    assert events == ["start", "shutdown"]


def test_worker_exits_when_scheduler_disabled(monkeypatch) -> None:
    events: list[str] = []
    container_called = {"value": False}

    def _fake_make_async_container(_provider):
        container_called["value"] = True
        return None

    monkeypatch.setattr(
        "pg_monitor.collector.worker.make_async_container",
        _fake_make_async_container,
    )

    asyncio.run(
        run_worker(
            settings=CollectorSettings(
                pg_dsn="postgresql://user:password@localhost:5432/monitoring",
                collector_scheduler_enabled=False,
            ),
            stop_event=asyncio.Event(),
        )
    )

    assert events == []
    assert container_called["value"] is False


def test_worker_retries_scheduler_startup_on_connection_error(
    monkeypatch,
) -> None:
    attempts = {"count": 0}
    events: list[str] = []
    sleep_calls: list[float] = []

    class DummyScheduler:
        async def start(self) -> None:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise CollectorConnectionError("db is unavailable")
            events.append("start")

        async def shutdown(self) -> None:
            events.append("shutdown")

    class DummyContainer:
        async def get(self, _dependency):
            return DummyScheduler()

        async def close(self) -> None:
            return None

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "pg_monitor.collector.worker.make_async_container",
        lambda _provider: DummyContainer(),
    )
    monkeypatch.setattr("pg_monitor.collector.worker.asyncio.sleep", fake_sleep)

    stop_event = asyncio.Event()
    stop_event.set()

    asyncio.run(
        run_worker(
            settings=CollectorSettings(
                pg_dsn="postgresql://user:password@localhost:5432/monitoring",
                collector_scheduler_enabled=True,
                collector_startup_retry_attempts=3,
                collector_startup_retry_base_delay_seconds=0.1,
                collector_startup_retry_max_delay_seconds=1.0,
            ),
            stop_event=stop_event,
        )
    )

    assert attempts["count"] == 3
    assert sleep_calls == [0.1, 0.2]
    assert events == ["start", "shutdown"]
