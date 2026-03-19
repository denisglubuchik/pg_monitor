from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Self

from pg_monitor.collector.models import (
    ActivitySnapshot,
    LocksSnapshot,
    RuntimeSnapshotResult,
)
from pg_monitor.collector.scheduler import CollectorScheduler
from pg_monitor.config import CollectorSettings


class FakeCollectorRepository:
    async def fetch_db_identifier(self) -> str:
        return "postgres@127.0.0.1:5432"


class FakeRuntimeSnapshotsRepository:
    def __init__(self) -> None:
        self.written: list[RuntimeSnapshotResult] = []

    async def write_runtime_snapshot(
        self,
        snapshot: RuntimeSnapshotResult,
    ) -> int:
        self.written.append(snapshot)
        return 1

    async def list_runtime_current(self) -> list[object]:
        return []


class FakeQuerySnapshotsRepository:
    async def write_query_snapshot(self, snapshot) -> int:
        del snapshot
        return 0


class FakeUnitOfWork:
    def __init__(self, runtime_repo: FakeRuntimeSnapshotsRepository) -> None:
        self.runtime_snapshots = runtime_repo
        self.query_snapshots = FakeQuerySnapshotsRepository()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


class FakeUnitOfWorkFactory:
    def __init__(self, runtime_repo: FakeRuntimeSnapshotsRepository) -> None:
        self.runtime_repo = runtime_repo

    def __call__(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self.runtime_repo)


def test_runtime_job_writes_runtime_snapshot(monkeypatch) -> None:
    runtime_repo = FakeRuntimeSnapshotsRepository()
    scheduler = CollectorScheduler(
        settings=CollectorSettings(
            pg_dsn="postgresql://user:password@localhost:5432/monitoring",
        ),
        repository=FakeCollectorRepository(),
        storage_uow_factory=FakeUnitOfWorkFactory(runtime_repo),
    )

    async def fake_collect_runtime_once(_repository):
        return RuntimeSnapshotResult(
            captured_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
            db_identifier="postgres@127.0.0.1:5432",
            activity=ActivitySnapshot(
                active_connections=1,
                blocked_sessions=0,
                longest_tx_duration_s=1.0,
            ),
            locks=LocksSnapshot(waiting_locks=0, granted_locks=1),
            database=[],
        )

    monkeypatch.setattr(
        "pg_monitor.collector.scheduler.collect_runtime_once",
        fake_collect_runtime_once,
    )

    asyncio.run(scheduler._run_runtime_job())

    assert len(runtime_repo.written) == 1
    assert runtime_repo.written[0].db_identifier == "postgres@127.0.0.1:5432"


def test_scheduler_start_runs_preflight_checks(monkeypatch) -> None:
    runtime_repo = FakeRuntimeSnapshotsRepository()
    scheduler = CollectorScheduler(
        settings=CollectorSettings(
            pg_dsn="postgresql://user:password@localhost:5432/monitoring",
        ),
        repository=FakeCollectorRepository(),
        storage_uow_factory=FakeUnitOfWorkFactory(runtime_repo),
    )

    monkeypatch.setattr(scheduler, "_run_runtime_job", lambda: asyncio.sleep(0))
    monkeypatch.setattr(scheduler, "_run_queries_job", lambda: asyncio.sleep(0))

    async def _run() -> None:
        await scheduler.start()
        await scheduler.shutdown()

    asyncio.run(_run())
