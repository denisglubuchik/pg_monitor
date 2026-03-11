from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime

import pytest

from pg_monitor.app import create_app
from pg_monitor.collector.models import (
    ActivitySnapshot,
    DatabaseMetric,
    LocksSnapshot,
    RuntimeSnapshotResult,
)
from pg_monitor.config import ApiSettings
from pg_monitor.storage import (
    StorageUnitOfWorkFactory,
    create_storage_engine,
    create_storage_session_factory,
)
from pg_monitor.storage.base import Base

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="docker binary is not available",
)
def test_runtime_metrics_snapshot_to_api_flow() -> None:
    pytest.importorskip("asyncpg")
    pytest.importorskip("testcontainers")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = _to_postgres_dsn(postgres.get_connection_url())
        asyncio.run(_exercise_runtime_metrics_flow(dsn))


async def _exercise_runtime_metrics_flow(storage_dsn: str) -> None:
    import httpx

    captured_at = datetime(2026, 3, 11, 10, 0, tzinfo=UTC)
    db_identifier = "postgres@127.0.0.1:5432"

    engine = create_storage_engine(storage_dsn)
    session_factory = create_storage_session_factory(engine)
    uow_factory = StorageUnitOfWorkFactory(session_factory)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with uow_factory() as uow:
        await uow.runtime_snapshots.write_runtime_snapshot(
            RuntimeSnapshotResult(
                captured_at=captured_at,
                db_identifier=db_identifier,
                activity=ActivitySnapshot(
                    active_connections=7,
                    blocked_sessions=1,
                    longest_tx_duration_s=14.0,
                ),
                locks=LocksSnapshot(waiting_locks=2, granted_locks=9),
                database=[
                    DatabaseMetric(
                        datid=5,
                        datname="postgres",
                        numbackends=3,
                        xact_commit=100,
                        xact_rollback=1,
                        blks_read=10,
                        blks_hit=150,
                        deadlocks=0,
                    )
                ],
            )
        )

    app = create_app(ApiSettings(storage_dsn=storage_dsn))
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/metrics",
                params={"db_identifier": db_identifier},
            )
    finally:
        await app.state.dishka_container.close()
        await engine.dispose()

    assert response.status_code == 200
    assert "pg_monitor_runtime_active_connections" in response.text
    assert (
        'pg_monitor_runtime_active_connections'
        '{db_identifier="postgres@127.0.0.1:5432"} 7.0'
    ) in response.text


def _to_postgres_dsn(connection_url: str) -> str:
    return connection_url.replace("postgresql+psycopg2://", "postgresql://", 1)
