from __future__ import annotations

from datetime import UTC, datetime

from pg_monitor.runtime_metrics import (
    RuntimeDatabaseMetrics,
    RuntimeMetricsExporter,
    RuntimeMetricsState,
)


def test_exporter_renders_runtime_metrics() -> None:
    exporter = RuntimeMetricsExporter()
    payload = exporter.render(
        states=[
            RuntimeMetricsState(
                captured_at=datetime(2026, 3, 11, 9, 58, tzinfo=UTC),
                db_identifier="postgres@127.0.0.1:5432",
                active_connections=8,
                blocked_sessions=1,
                longest_tx_duration_s=3.5,
                waiting_locks=2,
                granted_locks=10,
                database=[
                    RuntimeDatabaseMetrics(
                        datid=1,
                        datname="postgres",
                        numbackends=3,
                        xact_commit=120,
                        xact_rollback=4,
                        blks_read=8,
                        blks_hit=80,
                        deadlocks=0,
                    )
                ],
            )
        ],
        observed_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
    )

    assert "pg_monitor_runtime_active_connections" in payload
    assert "pg_monitor_runtime_snapshot_age_seconds" in payload
    assert "pg_monitor_runtime_db_deadlocks" in payload
    assert 'db_identifier="postgres@127.0.0.1:5432"' in payload
    assert 'datname="postgres"' in payload
