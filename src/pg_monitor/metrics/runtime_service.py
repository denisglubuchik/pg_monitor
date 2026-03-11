from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol, Self

from .runtime_models import RuntimeDatabaseMetrics, RuntimeMetricsState

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import TracebackType

    from pg_monitor.storage import RuntimeState


class RuntimeSnapshotReader(Protocol):
    async def get_runtime_current(
        self,
        *,
        db_identifier: str,
    ) -> RuntimeState | None: ...

    async def list_runtime_current(self) -> list[RuntimeState]: ...


class RuntimeMetricsUnitOfWork(Protocol):
    runtime_snapshots: RuntimeSnapshotReader

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class RuntimeMetricsService:
    def __init__(
        self,
        uow_factory: Callable[[], RuntimeMetricsUnitOfWork],
    ) -> None:
        self._uow_factory = uow_factory

    async def get_metrics_state(
        self,
        *,
        db_identifier: str | None = None,
    ) -> list[RuntimeMetricsState]:
        async with self._uow_factory() as uow:
            if db_identifier is None:
                states = await uow.runtime_snapshots.list_runtime_current()
            else:
                state = await uow.runtime_snapshots.get_runtime_current(
                    db_identifier=db_identifier
                )
                states = [] if state is None else [state]

        return [_to_runtime_metrics_state(state) for state in states]

    def current_time(self) -> datetime:
        return datetime.now(UTC)


def _to_runtime_metrics_state(state: RuntimeState) -> RuntimeMetricsState:
    return RuntimeMetricsState(
        captured_at=state.captured_at,
        db_identifier=state.db_identifier,
        active_connections=state.active_connections,
        blocked_sessions=state.blocked_sessions,
        longest_tx_duration_s=state.longest_tx_duration_s,
        waiting_locks=state.waiting_locks,
        granted_locks=state.granted_locks,
        database=[
            RuntimeDatabaseMetrics(
                datid=item.datid,
                datname=item.datname,
                numbackends=item.numbackends,
                xact_commit=item.xact_commit,
                xact_rollback=item.xact_rollback,
                blks_read=item.blks_read,
                blks_hit=item.blks_hit,
                deadlocks=item.deadlocks,
            )
            for item in state.database
        ],
    )
