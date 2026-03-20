from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from .api_service_metrics import ServiceMetrics
    from .runtime_models import RuntimeMetricsState

try:
    from prometheus_client import CollectorRegistry, Gauge, generate_latest
    from prometheus_client.exposition import CONTENT_TYPE_LATEST

    _PROMETHEUS_CLIENT_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback path
    _PROMETHEUS_CLIENT_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

class _RuntimeGaugeSet:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.active_connections = Gauge(
            "pg_monitor_runtime_active_connections",
            "Active PostgreSQL connections from pg_stat_activity.",
            ["db_identifier"],
            registry=registry,
        )
        self.blocked_sessions = Gauge(
            "pg_monitor_runtime_blocked_sessions",
            "Blocked sessions waiting on lock.",
            ["db_identifier"],
            registry=registry,
        )
        self.longest_tx = Gauge(
            "pg_monitor_runtime_longest_tx_duration_seconds",
            "Longest transaction duration in seconds.",
            ["db_identifier"],
            registry=registry,
        )
        self.waiting_locks = Gauge(
            "pg_monitor_runtime_waiting_locks",
            "Waiting locks count from pg_locks.",
            ["db_identifier"],
            registry=registry,
        )
        self.granted_locks = Gauge(
            "pg_monitor_runtime_granted_locks",
            "Granted locks count from pg_locks.",
            ["db_identifier"],
            registry=registry,
        )
        self.snapshot_age = Gauge(
            "pg_monitor_runtime_snapshot_age_seconds",
            "Age of the latest runtime snapshot in seconds.",
            ["db_identifier"],
            registry=registry,
        )
        self.db_numbackends = Gauge(
            "pg_monitor_runtime_db_numbackends",
            "Number of backends from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=registry,
        )
        self.db_xact_commit = Gauge(
            "pg_monitor_runtime_db_xact_commit",
            "Transactions committed from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=registry,
        )
        self.db_xact_rollback = Gauge(
            "pg_monitor_runtime_db_xact_rollback",
            "Transactions rolled back from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=registry,
        )
        self.db_blks_read = Gauge(
            "pg_monitor_runtime_db_blks_read",
            "Blocks read from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=registry,
        )
        self.db_blks_hit = Gauge(
            "pg_monitor_runtime_db_blks_hit",
            "Blocks hit from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=registry,
        )
        self.db_deadlocks = Gauge(
            "pg_monitor_runtime_db_deadlocks",
            "Deadlocks from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=registry,
        )


class RuntimeMetricsExporter:
    def __init__(self, service_metrics: "ServiceMetrics") -> None:
        self._service_metrics = service_metrics

    def render(
        self,
        *,
        states: list["RuntimeMetricsState"],
        observed_at: "datetime",
    ) -> str:
        if _PROMETHEUS_CLIENT_AVAILABLE:
            return self._render_with_prometheus_client(
                states=states,
                observed_at=observed_at,
            )
        return _render_fallback(states=states, observed_at=observed_at)

    def _render_with_prometheus_client(
        self,
        *,
        states: list["RuntimeMetricsState"],
        observed_at: "datetime",
    ) -> str:
        runtime_registry = CollectorRegistry(auto_describe=True)
        gauges = _RuntimeGaugeSet(runtime_registry)

        for state in states:
            labels = {"db_identifier": state.db_identifier}
            gauges.active_connections.labels(**labels).set(
                state.active_connections
            )
            gauges.blocked_sessions.labels(**labels).set(
                state.blocked_sessions
            )
            gauges.longest_tx.labels(**labels).set(
                state.longest_tx_duration_s or 0.0
            )
            gauges.waiting_locks.labels(**labels).set(
                state.waiting_locks
            )
            gauges.granted_locks.labels(**labels).set(
                state.granted_locks
            )
            gauges.snapshot_age.labels(**labels).set(
                max((observed_at - state.captured_at).total_seconds(), 0.0)
            )

            for db in state.database:
                db_labels = {
                    "db_identifier": state.db_identifier,
                    "datname": db.datname,
                }
                gauges.db_numbackends.labels(**db_labels).set(
                    db.numbackends
                )
                gauges.db_xact_commit.labels(**db_labels).set(
                    db.xact_commit
                )
                gauges.db_xact_rollback.labels(**db_labels).set(
                    db.xact_rollback
                )
                gauges.db_blks_read.labels(**db_labels).set(db.blks_read)
                gauges.db_blks_hit.labels(**db_labels).set(db.blks_hit)
                gauges.db_deadlocks.labels(**db_labels).set(db.deadlocks)

        runtime_payload = generate_latest(runtime_registry).decode("utf-8")
        service_payload = generate_latest(self._service_metrics.registry).decode(
            "utf-8"
        )
        return _merge_prometheus_payloads(runtime_payload, service_payload)


def _render_fallback(
    *,
    states: list["RuntimeMetricsState"],
    observed_at: "datetime",
) -> str:
    lines: list[str] = []
    for state in states:
        db_identifier = _escape_label(state.db_identifier)
        labels = f'db_identifier="{db_identifier}"'
        age_seconds = max(
            (observed_at - state.captured_at).total_seconds(),
            0.0,
        )
        lines.extend(
            [
                "# TYPE pg_monitor_runtime_active_connections gauge",
                (
                    "pg_monitor_runtime_active_connections"
                    f"{{{labels}}} {state.active_connections}"
                ),
                "# TYPE pg_monitor_runtime_blocked_sessions gauge",
                (
                    "pg_monitor_runtime_blocked_sessions"
                    f"{{{labels}}} {state.blocked_sessions}"
                ),
                "# TYPE pg_monitor_runtime_longest_tx_duration_seconds gauge",
                (
                    "pg_monitor_runtime_longest_tx_duration_seconds"
                    f"{{{labels}}} {state.longest_tx_duration_s or 0.0}"
                ),
                "# TYPE pg_monitor_runtime_waiting_locks gauge",
                (
                    "pg_monitor_runtime_waiting_locks"
                    f"{{{labels}}} {state.waiting_locks}"
                ),
                "# TYPE pg_monitor_runtime_granted_locks gauge",
                (
                    "pg_monitor_runtime_granted_locks"
                    f"{{{labels}}} {state.granted_locks}"
                ),
                "# TYPE pg_monitor_runtime_snapshot_age_seconds gauge",
                (
                    "pg_monitor_runtime_snapshot_age_seconds"
                    f"{{{labels}}} {age_seconds}"
                ),
            ]
        )
        for db in state.database:
            datname = _escape_label(db.datname)
            db_labels = f'{labels},datname="{datname}"'
            lines.extend(
                [
                    "# TYPE pg_monitor_runtime_db_numbackends gauge",
                    (
                        "pg_monitor_runtime_db_numbackends"
                        f"{{{db_labels}}} {db.numbackends}"
                    ),
                    "# TYPE pg_monitor_runtime_db_xact_commit gauge",
                    (
                        "pg_monitor_runtime_db_xact_commit"
                        f"{{{db_labels}}} {db.xact_commit}"
                    ),
                    "# TYPE pg_monitor_runtime_db_xact_rollback gauge",
                    (
                        "pg_monitor_runtime_db_xact_rollback"
                        f"{{{db_labels}}} {db.xact_rollback}"
                    ),
                    "# TYPE pg_monitor_runtime_db_blks_read gauge",
                    (
                        "pg_monitor_runtime_db_blks_read"
                        f"{{{db_labels}}} {db.blks_read}"
                    ),
                    "# TYPE pg_monitor_runtime_db_blks_hit gauge",
                    (
                        "pg_monitor_runtime_db_blks_hit"
                        f"{{{db_labels}}} {db.blks_hit}"
                    ),
                    "# TYPE pg_monitor_runtime_db_deadlocks gauge",
                    (
                        "pg_monitor_runtime_db_deadlocks"
                        f"{{{db_labels}}} {db.deadlocks}"
                    ),
                ]
            )
    if not lines:
        return "\n"
    return "\n".join(lines) + "\n"


def _escape_label(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("\n", "\\n")
    return escaped.replace('"', '\\"')


def _merge_prometheus_payloads(*payloads: str) -> str:
    chunks = [item.rstrip("\n") for item in payloads if item.strip()]
    if not chunks:
        return "\n"
    return "\n".join(chunks) + "\n"
