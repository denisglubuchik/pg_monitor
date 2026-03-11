from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class RuntimeDatabaseMetrics:
    datid: int
    datname: str
    numbackends: int
    xact_commit: int
    xact_rollback: int
    blks_read: int
    blks_hit: int
    deadlocks: int


@dataclass(frozen=True, slots=True)
class RuntimeMetricsState:
    captured_at: datetime
    db_identifier: str
    active_connections: int
    blocked_sessions: int
    longest_tx_duration_s: float | None
    waiting_locks: int
    granted_locks: int
    database: list[RuntimeDatabaseMetrics]
