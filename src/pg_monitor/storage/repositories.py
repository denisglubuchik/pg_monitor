from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from .errors import StorageReadError, StorageWriteError
from .models import (
    QuerySnapshotPoint,
    QuerySnapshotRow,
    RuntimeDatabaseState,
    RuntimeState,
)
from .orm import (
    QueryMetricSnapshotOrm,
    RuntimeCurrentOrm,
    RuntimeDatabaseCurrentOrm,
    RuntimeDatabaseSnapshotOrm,
    RuntimeSnapshotOrm,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.ext.asyncio import AsyncSession

    from pg_monitor.collector.models import (
        QuerySnapshotResult,
        RuntimeSnapshotResult,
    )


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


class RuntimeSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def write_runtime_snapshot(
        self,
        snapshot: RuntimeSnapshotResult,
    ) -> int:
        runtime_orm = RuntimeSnapshotOrm(
            captured_at=snapshot.captured_at,
            db_identifier=snapshot.db_identifier,
            active_connections=snapshot.activity.active_connections,
            blocked_sessions=snapshot.activity.blocked_sessions,
            longest_tx_duration_s=snapshot.activity.longest_tx_duration_s,
            waiting_locks=snapshot.locks.waiting_locks,
            granted_locks=snapshot.locks.granted_locks,
        )
        try:
            self._session.add(runtime_orm)
            await self._session.flush()

            history_rows = [
                RuntimeDatabaseSnapshotOrm(
                    runtime_snapshot_id=runtime_orm.id,
                    datid=row.datid,
                    datname=row.datname,
                    numbackends=row.numbackends,
                    xact_commit=row.xact_commit,
                    xact_rollback=row.xact_rollback,
                    blks_read=row.blks_read,
                    blks_hit=row.blks_hit,
                    deadlocks=row.deadlocks,
                )
                for row in snapshot.database
            ]
            if history_rows:
                self._session.add_all(history_rows)

            await self._upsert_runtime_current(snapshot)
            await self._upsert_runtime_database_current(snapshot)
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise StorageWriteError(
                f"failed to write runtime snapshot: {exc}"
            ) from exc

        return 1 + len(history_rows)

    async def get_runtime_current(
        self,
        *,
        db_identifier: str,
    ) -> RuntimeState | None:
        states = await self._load_runtime_states(db_identifier=db_identifier)
        return states[0] if states else None

    async def list_runtime_current(self) -> list[RuntimeState]:
        return await self._load_runtime_states(db_identifier=None)

    async def _load_runtime_states(
        self,
        *,
        db_identifier: str | None,
    ) -> list[RuntimeState]:
        try:
            base_query = select(RuntimeCurrentOrm).order_by(
                RuntimeCurrentOrm.db_identifier
            )
            if db_identifier is not None:
                base_query = base_query.where(
                    RuntimeCurrentOrm.db_identifier == db_identifier
                )

            current_rows = list(await self._session.scalars(base_query))
            if not current_rows:
                return []

            identifiers = [row.db_identifier for row in current_rows]
            db_rows = list(
                await self._session.scalars(
                    select(RuntimeDatabaseCurrentOrm)
                    .where(
                        RuntimeDatabaseCurrentOrm.db_identifier.in_(
                            identifiers
                        )
                    )
                    .order_by(
                        RuntimeDatabaseCurrentOrm.db_identifier,
                        RuntimeDatabaseCurrentOrm.datname,
                    )
                )
            )
        except SQLAlchemyError as exc:
            raise StorageReadError(
                f"failed to load runtime state for metrics: {exc}"
            ) from exc

        grouped: dict[str, list[RuntimeDatabaseState]] = {
            identifier: [] for identifier in identifiers
        }
        for row in db_rows:
            grouped[row.db_identifier].append(
                RuntimeDatabaseState(
                    datid=row.datid,
                    datname=row.datname,
                    numbackends=row.numbackends,
                    xact_commit=row.xact_commit,
                    xact_rollback=row.xact_rollback,
                    blks_read=row.blks_read,
                    blks_hit=row.blks_hit,
                    deadlocks=row.deadlocks,
                )
            )

        return [
            RuntimeState(
                captured_at=row.captured_at,
                db_identifier=row.db_identifier,
                active_connections=row.active_connections,
                blocked_sessions=row.blocked_sessions,
                longest_tx_duration_s=row.longest_tx_duration_s,
                waiting_locks=row.waiting_locks,
                granted_locks=row.granted_locks,
                database=grouped[row.db_identifier],
            )
            for row in current_rows
        ]

    async def _upsert_runtime_current(
        self,
        snapshot: RuntimeSnapshotResult,
    ) -> None:
        statement = insert(RuntimeCurrentOrm).values(
            db_identifier=snapshot.db_identifier,
            captured_at=snapshot.captured_at,
            active_connections=snapshot.activity.active_connections,
            blocked_sessions=snapshot.activity.blocked_sessions,
            longest_tx_duration_s=snapshot.activity.longest_tx_duration_s,
            waiting_locks=snapshot.locks.waiting_locks,
            granted_locks=snapshot.locks.granted_locks,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[RuntimeCurrentOrm.db_identifier],
            set_={
                "captured_at": statement.excluded.captured_at,
                "active_connections": statement.excluded.active_connections,
                "blocked_sessions": statement.excluded.blocked_sessions,
                "longest_tx_duration_s": (
                    statement.excluded.longest_tx_duration_s
                ),
                "waiting_locks": statement.excluded.waiting_locks,
                "granted_locks": statement.excluded.granted_locks,
            },
        )
        await self._session.execute(statement)

    async def _upsert_runtime_database_current(
        self,
        snapshot: RuntimeSnapshotResult,
    ) -> None:
        datnames = [row.datname for row in snapshot.database]
        if datnames:
            await self._session.execute(
                delete(RuntimeDatabaseCurrentOrm).where(
                    RuntimeDatabaseCurrentOrm.db_identifier
                    == snapshot.db_identifier,
                    RuntimeDatabaseCurrentOrm.datname.not_in(datnames),
                )
            )
        else:
            await self._session.execute(
                delete(RuntimeDatabaseCurrentOrm).where(
                    RuntimeDatabaseCurrentOrm.db_identifier
                    == snapshot.db_identifier
                )
            )
            return

        values = [
            {
                "db_identifier": snapshot.db_identifier,
                "captured_at": snapshot.captured_at,
                "datid": row.datid,
                "datname": row.datname,
                "numbackends": row.numbackends,
                "xact_commit": row.xact_commit,
                "xact_rollback": row.xact_rollback,
                "blks_read": row.blks_read,
                "blks_hit": row.blks_hit,
                "deadlocks": row.deadlocks,
            }
            for row in snapshot.database
        ]
        statement = insert(RuntimeDatabaseCurrentOrm).values(values)
        statement = statement.on_conflict_do_update(
            constraint="uq_runtime_database_current_db_identifier_datname",
            set_={
                "captured_at": statement.excluded.captured_at,
                "datid": statement.excluded.datid,
                "numbackends": statement.excluded.numbackends,
                "xact_commit": statement.excluded.xact_commit,
                "xact_rollback": statement.excluded.xact_rollback,
                "blks_read": statement.excluded.blks_read,
                "blks_hit": statement.excluded.blks_hit,
                "deadlocks": statement.excluded.deadlocks,
            },
        )
        await self._session.execute(statement)
