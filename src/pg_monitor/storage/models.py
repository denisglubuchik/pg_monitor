from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from .orm import QueryMetricSnapshotOrm


@dataclass(frozen=True, slots=True)
class QuerySnapshotRow:
    captured_at: datetime
    db_identifier: str
    queryid: str
    dbid: int
    userid: int
    query: str
    calls: int
    total_exec_time_ms: float
    mean_exec_time_ms: float
    rows: int
    shared_blks_hit: int
    shared_blks_read: int
    shared_blks_dirtied: int
    shared_blks_written: int

    @classmethod
    def from_orm(cls, row: QueryMetricSnapshotOrm) -> QuerySnapshotRow:
        return cls(
            captured_at=row.captured_at,
            db_identifier=row.db_identifier,
            queryid=row.queryid,
            dbid=row.dbid,
            userid=row.userid,
            query=row.query,
            calls=row.calls,
            total_exec_time_ms=row.total_exec_time_ms,
            mean_exec_time_ms=row.mean_exec_time_ms,
            rows=row.rows,
            shared_blks_hit=row.shared_blks_hit,
            shared_blks_read=row.shared_blks_read,
            shared_blks_dirtied=row.shared_blks_dirtied,
            shared_blks_written=row.shared_blks_written,
        )


@dataclass(frozen=True, slots=True)
class QuerySnapshotPoint:
    captured_at: datetime
    rows: list[QuerySnapshotRow]


@dataclass(frozen=True, slots=True)
class RuntimeDatabaseState:
    datid: int
    datname: str
    numbackends: int
    xact_commit: int
    xact_rollback: int
    blks_read: int
    blks_hit: int
    deadlocks: int


@dataclass(frozen=True, slots=True)
class RuntimeState:
    captured_at: datetime
    db_identifier: str
    active_connections: int
    blocked_sessions: int
    longest_tx_duration_s: float | None
    waiting_locks: int
    granted_locks: int
    database: list[RuntimeDatabaseState]
