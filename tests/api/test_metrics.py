from __future__ import annotations

from datetime import UTC, datetime

from pg_monitor.runtime_metrics import (
    RuntimeDatabaseMetrics,
    RuntimeMetricsService,
    RuntimeMetricsState,
)


def test_metrics_endpoint_returns_prometheus_payload(
    client,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 3, 11, 10, 0, tzinfo=UTC)

    async def fake_get_metrics_state(
        self: RuntimeMetricsService,
        *,
        db_identifier: str | None = None,
    ) -> list[RuntimeMetricsState]:
        del self, db_identifier
        return [
            RuntimeMetricsState(
                captured_at=datetime(2026, 3, 11, 9, 59, tzinfo=UTC),
                db_identifier="postgres@127.0.0.1:5432",
                active_connections=11,
                blocked_sessions=1,
                longest_tx_duration_s=12.5,
                waiting_locks=2,
                granted_locks=20,
                database=[
                    RuntimeDatabaseMetrics(
                        datid=5,
                        datname="postgres",
                        numbackends=5,
                        xact_commit=100,
                        xact_rollback=2,
                        blks_read=10,
                        blks_hit=200,
                        deadlocks=0,
                    )
                ],
            )
        ]

    monkeypatch.setattr(
        RuntimeMetricsService,
        "get_metrics_state",
        fake_get_metrics_state,
    )
    monkeypatch.setattr(
        RuntimeMetricsService,
        "current_time",
        lambda _: fixed_now,
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "pg_monitor_runtime_active_connections" in response.text
    assert 'db_identifier="postgres@127.0.0.1:5432"' in response.text


def test_metrics_endpoint_passes_db_identifier_filter(
    client,
    monkeypatch,
) -> None:
    calls: list[str | None] = []

    async def fake_get_metrics_state(
        self: RuntimeMetricsService,
        *,
        db_identifier: str | None = None,
    ) -> list[RuntimeMetricsState]:
        del self
        calls.append(db_identifier)
        return []

    monkeypatch.setattr(
        RuntimeMetricsService,
        "get_metrics_state",
        fake_get_metrics_state,
    )

    response = client.get(
        "/metrics",
        params={"db_identifier": "postgres@127.0.0.1:5432"},
    )

    assert response.status_code == 200
    assert calls == ["postgres@127.0.0.1:5432"]
