from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from pg_monitor.app import create_app
from pg_monitor.collector import CollectorConnectionError
from pg_monitor.collector.worker import run_worker
from pg_monitor.config import ApiSettings, CollectorSettings


def test_app_has_no_embedded_collector_scheduler() -> None:
    app = create_app(
        ApiSettings()
    )

    with TestClient(app) as client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert not hasattr(client.app.state, "collector_scheduler")


def test_worker_starts_and_stops_scheduler(monkeypatch) -> None:
    events: list[str] = []

    class DummyScheduler:
        def __init__(self, settings: CollectorSettings) -> None:
            self._settings = settings

        async def start(self) -> None:
            events.append("start")

        async def shutdown(self) -> None:
            events.append("shutdown")

    monkeypatch.setattr(
        "pg_monitor.collector.worker.CollectorScheduler",
        DummyScheduler,
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

    class DummyScheduler:
        def __init__(self, settings: CollectorSettings) -> None:
            self._settings = settings

        async def start(self) -> None:
            events.append("start")

        async def shutdown(self) -> None:
            events.append("shutdown")

    monkeypatch.setattr(
        "pg_monitor.collector.worker.CollectorScheduler",
        DummyScheduler,
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


def test_worker_retries_scheduler_startup_on_connection_error(
    monkeypatch,
) -> None:
    attempts = {"count": 0}
    events: list[str] = []
    sleep_calls: list[float] = []

    class DummyScheduler:
        def __init__(self, settings: CollectorSettings) -> None:
            self._settings = settings

        async def start(self) -> None:
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise CollectorConnectionError("db is unavailable")
            events.append("start")

        async def shutdown(self) -> None:
            events.append("shutdown")

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(
        "pg_monitor.collector.worker.CollectorScheduler",
        DummyScheduler,
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
