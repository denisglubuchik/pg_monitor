from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from datetime import datetime


def _require_value(row: Mapping[str, object], key: str) -> object:
    if key not in row:
        msg = f"required key is missing in collector row: {key}"
        raise ValueError(msg)
    value = row[key]
    if value is None:
        msg = f"required key has null value in collector row: {key}"
        raise ValueError(msg)
    return value


def _to_int(row: Mapping[str, object], key: str) -> int:
    return int(_require_value(row, key))


def _to_float(row: Mapping[str, object], key: str) -> float:
    return float(_require_value(row, key))


def _to_str(row: Mapping[str, object], key: str) -> str:
    return str(_require_value(row, key))


@dataclass(frozen=True, slots=True)
class StatementMetric:
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
    def from_row(cls, row: Mapping[str, object]) -> StatementMetric:
        return cls(
            queryid=_to_str(row, "queryid"),
            dbid=_to_int(row, "dbid"),
            userid=_to_int(row, "userid"),
            query=_to_str(row, "query"),
            calls=_to_int(row, "calls"),
            total_exec_time_ms=_to_float(row, "total_exec_time_ms"),
            mean_exec_time_ms=_to_float(row, "mean_exec_time_ms"),
            rows=_to_int(row, "rows"),
            shared_blks_hit=_to_int(row, "shared_blks_hit"),
            shared_blks_read=_to_int(row, "shared_blks_read"),
            shared_blks_dirtied=_to_int(row, "shared_blks_dirtied"),
            shared_blks_written=_to_int(row, "shared_blks_written"),
        )


@dataclass(frozen=True, slots=True)
class ActivitySnapshot:
    active_connections: int
    blocked_sessions: int
    longest_tx_duration_s: float | None

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> ActivitySnapshot:
        if "longest_tx_duration_s" not in row:
            msg = (
                "required key is missing in collector row: "
                "longest_tx_duration_s"
            )
            raise ValueError(msg)
        longest_tx = row["longest_tx_duration_s"]
        return cls(
            active_connections=_to_int(row, "active_connections"),
            blocked_sessions=_to_int(row, "blocked_sessions"),
            longest_tx_duration_s=None
            if longest_tx is None
            else float(longest_tx),
        )


@dataclass(frozen=True, slots=True)
class LocksSnapshot:
    waiting_locks: int
    granted_locks: int

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> LocksSnapshot:
        return cls(
            waiting_locks=_to_int(row, "waiting_locks"),
            granted_locks=_to_int(row, "granted_locks"),
        )


@dataclass(frozen=True, slots=True)
class DatabaseMetric:
    datid: int
    datname: str
    numbackends: int
    xact_commit: int
    xact_rollback: int
    blks_read: int
    blks_hit: int
    deadlocks: int

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> DatabaseMetric:
        return cls(
            datid=_to_int(row, "datid"),
            datname=_to_str(row, "datname"),
            numbackends=_to_int(row, "numbackends"),
            xact_commit=_to_int(row, "xact_commit"),
            xact_rollback=_to_int(row, "xact_rollback"),
            blks_read=_to_int(row, "blks_read"),
            blks_hit=_to_int(row, "blks_hit"),
            deadlocks=_to_int(row, "deadlocks"),
        )


@dataclass(frozen=True, slots=True)
class RuntimeSnapshotResult:
    captured_at: datetime
    db_identifier: str
    activity: ActivitySnapshot
    locks: LocksSnapshot
    database: list[DatabaseMetric]


@dataclass(frozen=True, slots=True)
class QuerySnapshotResult:
    captured_at: datetime
    db_identifier: str
    statements: list[StatementMetric]
