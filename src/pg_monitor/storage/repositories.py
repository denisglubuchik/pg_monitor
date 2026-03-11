from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from .errors import StorageReadError, StorageWriteError
from .models import QuerySnapshotPoint, QuerySnapshotRow
from .orm import QueryMetricSnapshotOrm

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from pg_monitor.collector.models import QuerySnapshotResult


class QuerySnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write_query_snapshot(
        self,
        snapshot: QuerySnapshotResult,
    ) -> int:
        if not snapshot.statements:
            return 0

        orm_rows = [
            QueryMetricSnapshotOrm(
                captured_at=snapshot.captured_at,
                db_identifier=snapshot.db_identifier,
                queryid=statement.queryid,
                dbid=statement.dbid,
                userid=statement.userid,
                query=statement.query,
                calls=statement.calls,
                total_exec_time_ms=statement.total_exec_time_ms,
                mean_exec_time_ms=statement.mean_exec_time_ms,
                rows=statement.rows,
                shared_blks_hit=statement.shared_blks_hit,
                shared_blks_read=statement.shared_blks_read,
                shared_blks_dirtied=statement.shared_blks_dirtied,
                shared_blks_written=statement.shared_blks_written,
            )
            for statement in snapshot.statements
        ]

        try:
            self._session.add_all(orm_rows)
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise StorageWriteError(
                f"failed to write query snapshot: {exc}"
            ) from exc

        return len(orm_rows)

    async def get_latest_snapshot_at_or_before(
        self,
        *,
        db_identifier: str,
        ts: datetime,
    ) -> QuerySnapshotPoint | None:
        try:
            latest_ts = await self._session.scalar(
                select(func.max(QueryMetricSnapshotOrm.captured_at)).where(
                    QueryMetricSnapshotOrm.db_identifier == db_identifier,
                    QueryMetricSnapshotOrm.captured_at <= ts,
                )
            )
            if latest_ts is None:
                return None

            result = await self._session.scalars(
                select(QueryMetricSnapshotOrm)
                .where(
                    QueryMetricSnapshotOrm.db_identifier == db_identifier,
                    QueryMetricSnapshotOrm.captured_at == latest_ts,
                )
                .order_by(
                    QueryMetricSnapshotOrm.queryid,
                    QueryMetricSnapshotOrm.dbid,
                    QueryMetricSnapshotOrm.userid,
                )
            )
            rows = [QuerySnapshotRow.from_orm(row) for row in result]
            return QuerySnapshotPoint(captured_at=latest_ts, rows=rows)
        except SQLAlchemyError as exc:
            raise StorageReadError(
                f"failed to load query snapshots for analytics: {exc}"
            ) from exc
