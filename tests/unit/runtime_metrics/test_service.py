from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Self

from pg_monitor.runtime_metrics import RuntimeMetricsService
from pg_monitor.storage import RuntimeDatabaseState, RuntimeState


class FakeRuntimeSnapshotRepository:
    def __init__(self, states: list[RuntimeState]) -> None:
        self._states = states

    async def list_runtime_current(self) -> list[RuntimeState]:
        return self._states

    async def get_runtime_current(
        self,
        *,
        db_identifier: str,
    ) -> RuntimeState | None:
        for state in self._states:
            if state.db_identifier == db_identifier:
                return state
        return None


class FakeUnitOfWork:
    def __init__(self, repository: FakeRuntimeSnapshotRepository) -> None:
        self.runtime_snapshots = repository

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb


class FakeUnitOfWorkFactory:
    def __init__(self, repository: FakeRuntimeSnapshotRepository) -> None:
        self._repository = repository

    def __call__(self) -> FakeUnitOfWork:
        return FakeUnitOfWork(self._repository)


def _sample_state(db_identifier: str) -> RuntimeState:
    return RuntimeState(
        captured_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
        db_identifier=db_identifier,
        active_connections=4,
        blocked_sessions=1,
        longest_tx_duration_s=7.0,
        waiting_locks=2,
        granted_locks=5,
        database=[
            RuntimeDatabaseState(
                datid=1,
                datname="postgres",
                numbackends=2,
                xact_commit=100,
                xact_rollback=3,
                blks_read=20,
                blks_hit=200,
                deadlocks=0,
            )
        ],
    )


def test_service_returns_all_states() -> None:
    service = RuntimeMetricsService(
        FakeUnitOfWorkFactory(
            FakeRuntimeSnapshotRepository(
                [_sample_state("db-1"), _sample_state("db-2")]
            )
        )
    )

    result = asyncio.run(service.get_metrics_state())

    assert len(result) == 2
    assert result[0].db_identifier == "db-1"


def test_service_filters_by_db_identifier() -> None:
    service = RuntimeMetricsService(
        FakeUnitOfWorkFactory(
            FakeRuntimeSnapshotRepository(
                [_sample_state("db-1"), _sample_state("db-2")]
            )
        )
    )

    result = asyncio.run(
        service.get_metrics_state(db_identifier="db-2")
    )

    assert len(result) == 1
    assert result[0].db_identifier == "db-2"
