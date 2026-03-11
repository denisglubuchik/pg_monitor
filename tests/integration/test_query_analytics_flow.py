from __future__ import annotations

import asyncio
import shutil
from datetime import UTC, datetime, timedelta

import pytest

from pg_monitor.app import create_app
from pg_monitor.collector.models import QuerySnapshotResult, StatementMetric
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
def test_query_analytics_snapshot_to_api_flow() -> None:
    pytest.importorskip("asyncpg")
    pytest.importorskip("testcontainers")

    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = _to_postgres_dsn(postgres.get_connection_url())
        asyncio.run(_exercise_snapshot_to_api_flow(dsn))


async def _exercise_snapshot_to_api_flow(storage_dsn: str) -> None:
    import httpx

    db_identifier = "postgres@127.0.0.1:5432"
    now = datetime.now(UTC)
    # weekly-top takes [now-7d, now], so we keep baseline before window start.
    start_at = now - timedelta(days=8)
    end_at = now - timedelta(minutes=1)

    engine = create_storage_engine(storage_dsn)
    session_factory = create_storage_session_factory(engine)
    uow_factory = StorageUnitOfWorkFactory(session_factory)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with uow_factory() as uow:
        await uow.query_snapshots.write_query_snapshot(
            QuerySnapshotResult(
                captured_at=start_at,
                db_identifier=db_identifier,
                statements=[
                    StatementMetric(
                        queryid="q1",
                        dbid=1,
                        userid=10,
                        query="SELECT 1",
                        calls=10,
                        total_exec_time_ms=100.0,
                        mean_exec_time_ms=10.0,
                        rows=10,
                        shared_blks_hit=0,
                        shared_blks_read=0,
                        shared_blks_dirtied=0,
                        shared_blks_written=0,
                    )
                ],
            )
        )

    async with uow_factory() as uow:
        await uow.query_snapshots.write_query_snapshot(
            QuerySnapshotResult(
                captured_at=end_at,
                db_identifier=db_identifier,
                statements=[
                    StatementMetric(
                        queryid="q1",
                        dbid=1,
                        userid=10,
                        query="SELECT 1",
                        calls=25,
                        total_exec_time_ms=220.0,
                        mean_exec_time_ms=8.8,
                        rows=25,
                        shared_blks_hit=0,
                        shared_blks_read=0,
                        shared_blks_dirtied=0,
                        shared_blks_written=0,
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
                "/analytics/queries/weekly-top",
                params={
                    "db_identifier": db_identifier,
                    "limit": 5,
                    "sort_by": "calls_delta",
                },
            )
    finally:
        await app.state.dishka_container.close()
        await engine.dispose()

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["queryid"] == "q1"
    assert payload["items"][0]["calls_delta"] == 15
    assert payload["items"][0]["total_exec_time_ms_delta"] == 120.0


def _to_postgres_dsn(connection_url: str) -> str:
    return connection_url.replace("postgresql+psycopg2://", "postgresql://", 1)
