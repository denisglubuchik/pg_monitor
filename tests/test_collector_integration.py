from __future__ import annotations

import asyncio
import shutil

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    shutil.which("docker") is None,
    reason="docker is not available",
)
def test_collectors_with_postgres_container() -> None:
    pytest.importorskip("asyncpg")
    pytest.importorskip("testcontainers")

    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer("postgres:16-alpine")
    if hasattr(container, "with_command"):
        container = container.with_command(
            "postgres -c shared_preload_libraries=pg_stat_statements"
        )

    with container as postgres:
        dsn = _to_asyncpg_dsn(postgres.get_connection_url())
        asyncio.run(_exercise_collectors(dsn))


async def _exercise_collectors(dsn: str) -> None:
    import asyncpg

    from pg_monitor.collector import (
        AsyncpgCollectorRepository,
        collect_queries_once,
        collect_runtime_once,
        create_pool,
    )

    pool = await create_pool(dsn, min_size=1, max_size=2)

    try:
        async with pool.acquire() as conn:
            try:
                await conn.execute(
                    "CREATE EXTENSION IF NOT EXISTS pg_stat_statements"
                )
            except asyncpg.PostgresError as exc:
                pytest.skip(f"pg_stat_statements is unavailable: {exc}")

            await conn.execute("SELECT 1")
            await conn.execute("SELECT 2")

        repository = AsyncpgCollectorRepository(pool)
        runtime_snapshot = await collect_runtime_once(repository)
        query_snapshot = await collect_queries_once(repository)
    finally:
        await pool.close()

    assert runtime_snapshot.db_identifier
    assert runtime_snapshot.activity.active_connections >= 0
    assert runtime_snapshot.locks.granted_locks >= 0
    assert runtime_snapshot.database

    assert query_snapshot.statements
    assert all(metric.queryid for metric in query_snapshot.statements)
    assert any(metric.query for metric in query_snapshot.statements)


def _to_asyncpg_dsn(connection_url: str) -> str:
    return connection_url.replace("postgresql+psycopg2://", "postgresql://", 1)
