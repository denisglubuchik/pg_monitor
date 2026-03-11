from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from pg_monitor.collector.models import QuerySnapshotResult, StatementMetric
from pg_monitor.storage import QuerySnapshotRepository, StorageReadError
from pg_monitor.storage.orm import QueryMetricSnapshotOrm


class FakeSession:
    def __init__(
        self,
        *,
        latest_ts: datetime | None = None,
        orm_rows: list[QueryMetricSnapshotOrm] | None = None,
        flush_error: Exception | None = None,
        scalar_error: Exception | None = None,
    ) -> None:
        self.latest_ts = latest_ts
        self.orm_rows = orm_rows or []
        self.flush_error = flush_error
        self.scalar_error = scalar_error
        self.added_rows: list[QueryMetricSnapshotOrm] = []

    def add_all(self, rows: list[QueryMetricSnapshotOrm]) -> None:
        self.added_rows.extend(rows)

    async def flush(self) -> None:
        if self.flush_error is not None:
            raise self.flush_error

    async def scalar(self, _statement):
        if self.scalar_error is not None:
            raise self.scalar_error
        return self.latest_ts

    async def scalars(self, _statement):
        return self.orm_rows


def _build_snapshot() -> QuerySnapshotResult:
    captured_at = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)
    return QuerySnapshotResult(
        captured_at=captured_at,
        db_identifier="postgres@127.0.0.1:5432",
        statements=[
            StatementMetric(
                queryid="q1",
                dbid=1,
                userid=10,
                query="SELECT 1",
                calls=7,
                total_exec_time_ms=18.2,
                mean_exec_time_ms=2.6,
                rows=7,
                shared_blks_hit=1,
                shared_blks_read=0,
                shared_blks_dirtied=0,
                shared_blks_written=0,
            ),
            StatementMetric(
                queryid="q2",
                dbid=1,
                userid=10,
                query="SELECT 2",
                calls=3,
                total_exec_time_ms=5.1,
                mean_exec_time_ms=1.7,
                rows=3,
                shared_blks_hit=0,
                shared_blks_read=1,
                shared_blks_dirtied=0,
                shared_blks_written=0,
            ),
        ],
    )


def test_write_query_snapshot_adds_all_rows() -> None:
    snapshot = _build_snapshot()
    session = FakeSession()
    repository = QuerySnapshotRepository(session)

    written = asyncio.run(repository.write_query_snapshot(snapshot))

    assert written == 2
    assert len(session.added_rows) == 2
    assert session.added_rows[0].queryid == "q1"
    assert session.added_rows[1].queryid == "q2"


def test_get_latest_snapshot_at_or_before_returns_rows() -> None:
    ts = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)
    orm_rows = [
        QueryMetricSnapshotOrm(
            captured_at=ts,
            db_identifier="postgres@127.0.0.1:5432",
            queryid="q1",
            dbid=1,
            userid=10,
            query="SELECT 1",
            calls=7,
            total_exec_time_ms=18.2,
            mean_exec_time_ms=2.6,
            rows=7,
            shared_blks_hit=1,
            shared_blks_read=0,
            shared_blks_dirtied=0,
            shared_blks_written=0,
        )
    ]
    session = FakeSession(latest_ts=ts, orm_rows=orm_rows)
    repository = QuerySnapshotRepository(session)

    point = asyncio.run(
        repository.get_latest_snapshot_at_or_before(
            db_identifier="postgres@127.0.0.1:5432",
            ts=ts,
        )
    )

    assert point is not None
    assert point.captured_at == ts
    assert len(point.rows) == 1
    assert point.rows[0].queryid == "q1"


def test_get_latest_snapshot_at_or_before_raises_storage_error() -> None:
    ts = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)
    session = FakeSession(scalar_error=SQLAlchemyError("boom"))
    repository = QuerySnapshotRepository(session)

    try:
        asyncio.run(
            repository.get_latest_snapshot_at_or_before(
                db_identifier="postgres@127.0.0.1:5432",
                ts=ts,
            )
        )
    except StorageReadError as exc:
        assert "failed to load query snapshots for analytics" in str(exc)
    else:
        raise AssertionError("StorageReadError was not raised")
