from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from pg_monitor.collector import (
    CollectorPrerequisiteError,
    CollectorQueryError,
    collect_queries_once,
    collect_runtime_once,
)


class FakeCollectorRepository:
    def __init__(self, *, extension_available: bool = True) -> None:
        self._extension_available = extension_available

    async def fetch_db_identifier(self) -> str:
        return "postgres@127.0.0.1:5432"

    async def is_pg_stat_statements_available(self) -> bool:
        return self._extension_available

    async def fetch_activity_row(self) -> dict[str, object]:
        return {
            "active_connections": 3,
            "blocked_sessions": 1,
            "longest_tx_duration_s": 12.5,
        }

    async def fetch_locks_row(self) -> dict[str, object]:
        return {"waiting_locks": 2, "granted_locks": 9}

    async def fetch_database_rows(self) -> list[dict[str, object]]:
        return [
            {
                "datid": 123,
                "datname": "postgres",
                "numbackends": 4,
                "xact_commit": 100,
                "xact_rollback": 2,
                "blks_read": 20,
                "blks_hit": 99,
                "deadlocks": 0,
            }
        ]

    async def fetch_runtime_rows(
        self,
    ) -> tuple[dict[str, object], dict[str, object], list[dict[str, object]]]:
        return (
            await self.fetch_activity_row(),
            await self.fetch_locks_row(),
            await self.fetch_database_rows(),
        )

    async def fetch_statement_rows(self) -> list[dict[str, object]]:
        return [
            {
                "queryid": "42",
                "dbid": 123,
                "userid": 10,
                "query": "SELECT 1",
                "calls": 7,
                "total_exec_time_ms": 18.2,
                "mean_exec_time_ms": 2.6,
                "rows": 7,
                "shared_blks_hit": 1,
                "shared_blks_read": 0,
                "shared_blks_dirtied": 0,
                "shared_blks_written": 0,
            }
        ]


def test_collect_runtime_once_returns_snapshot() -> None:
    fixed_now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    repo = FakeCollectorRepository()

    snapshot = asyncio.run(
        collect_runtime_once(repo, now_provider=lambda: fixed_now)
    )

    assert snapshot.captured_at == fixed_now
    assert snapshot.db_identifier == "postgres@127.0.0.1:5432"
    assert snapshot.activity.active_connections == 3
    assert snapshot.locks.waiting_locks == 2
    assert len(snapshot.database) == 1
    assert snapshot.database[0].datname == "postgres"


def test_collect_queries_once_returns_snapshot_with_query_text() -> None:
    fixed_now = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    repo = FakeCollectorRepository()

    snapshot = asyncio.run(
        collect_queries_once(repo, now_provider=lambda: fixed_now)
    )

    assert snapshot.captured_at == fixed_now
    assert snapshot.db_identifier == "postgres@127.0.0.1:5432"
    assert len(snapshot.statements) == 1
    statement = snapshot.statements[0]
    assert statement.queryid == "42"
    assert statement.query == "SELECT 1"


def test_collect_queries_once_fails_without_pg_stat_statements() -> None:
    repo = FakeCollectorRepository(extension_available=False)

    try:
        asyncio.run(collect_queries_once(repo))
    except CollectorPrerequisiteError as exc:
        assert "pg_stat_statements" in str(exc)
    else:
        raise AssertionError("CollectorPrerequisiteError was not raised")


def test_collect_runtime_once_fails_on_invalid_row_shape() -> None:
    class BrokenRuntimeRepository(FakeCollectorRepository):
        async def fetch_activity_row(self) -> dict[str, object]:
            return {"blocked_sessions": 1, "longest_tx_duration_s": 3.0}

    repo = BrokenRuntimeRepository()

    try:
        asyncio.run(collect_runtime_once(repo))
    except CollectorQueryError as exc:
        assert "runtime cycle failed" in str(exc)
    else:
        raise AssertionError("CollectorQueryError was not raised")


def test_collect_runtime_once_uses_runtime_bundle_when_available() -> None:
    class BundleRepository(FakeCollectorRepository):
        def __init__(self) -> None:
            super().__init__()
            self.bundle_calls = 0

        async def fetch_runtime_rows(
            self,
        ) -> tuple[
            dict[str, object],
            dict[str, object],
            list[dict[str, object]],
        ]:
            self.bundle_calls += 1
            return (
                {
                    "active_connections": 3,
                    "blocked_sessions": 1,
                    "longest_tx_duration_s": 12.5,
                },
                {"waiting_locks": 2, "granted_locks": 9},
                [
                    {
                        "datid": 123,
                        "datname": "postgres",
                        "numbackends": 4,
                        "xact_commit": 100,
                        "xact_rollback": 2,
                        "blks_read": 20,
                        "blks_hit": 99,
                        "deadlocks": 0,
                    }
                ],
            )

        async def fetch_activity_row(self) -> dict[str, object]:
            raise AssertionError("fetch_activity_row should not be used")

        async def fetch_locks_row(self) -> dict[str, object]:
            raise AssertionError("fetch_locks_row should not be used")

        async def fetch_database_rows(self) -> list[dict[str, object]]:
            raise AssertionError("fetch_database_rows should not be used")

    repo = BundleRepository()
    snapshot = asyncio.run(collect_runtime_once(repo))

    assert snapshot.db_identifier == "postgres@127.0.0.1:5432"
    assert repo.bundle_calls == 1


def test_collect_queries_once_fails_on_invalid_row_shape() -> None:
    class BrokenQueryRepository(FakeCollectorRepository):
        async def fetch_statement_rows(self) -> list[dict[str, object]]:
            return [
                {
                    "dbid": 1,
                    "userid": 1,
                    "query": "SELECT 1",
                    "calls": 1,
                    "total_exec_time_ms": 1.0,
                    "mean_exec_time_ms": 1.0,
                    "rows": 1,
                    "shared_blks_hit": 0,
                    "shared_blks_read": 0,
                    "shared_blks_dirtied": 0,
                    "shared_blks_written": 0,
                }
            ]

    repo = BrokenQueryRepository()

    try:
        asyncio.run(collect_queries_once(repo))
    except CollectorQueryError as exc:
        assert "query cycle failed" in str(exc)
    else:
        raise AssertionError("CollectorQueryError was not raised")
