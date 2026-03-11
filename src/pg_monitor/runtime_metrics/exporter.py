from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from .models import RuntimeMetricsState

try:
    from prometheus_client import CollectorRegistry, Gauge, generate_latest
    from prometheus_client.exposition import CONTENT_TYPE_LATEST

    _PROMETHEUS_CLIENT_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback path
    _PROMETHEUS_CLIENT_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"


class RuntimeMetricsExporter:
    def __init__(self) -> None:
        if not _PROMETHEUS_CLIENT_AVAILABLE:
            return

        self._registry = CollectorRegistry(auto_describe=True)
        self._active_connections = Gauge(
            "pg_monitor_runtime_active_connections",
            "Active PostgreSQL connections from pg_stat_activity.",
            ["db_identifier"],
            registry=self._registry,
        )
        self._blocked_sessions = Gauge(
            "pg_monitor_runtime_blocked_sessions",
            "Blocked sessions waiting on lock.",
            ["db_identifier"],
            registry=self._registry,
        )
        self._longest_tx = Gauge(
            "pg_monitor_runtime_longest_tx_duration_seconds",
            "Longest transaction duration in seconds.",
            ["db_identifier"],
            registry=self._registry,
        )
        self._waiting_locks = Gauge(
            "pg_monitor_runtime_waiting_locks",
            "Waiting locks count from pg_locks.",
            ["db_identifier"],
            registry=self._registry,
        )
        self._granted_locks = Gauge(
            "pg_monitor_runtime_granted_locks",
            "Granted locks count from pg_locks.",
            ["db_identifier"],
            registry=self._registry,
        )
        self._snapshot_age = Gauge(
            "pg_monitor_runtime_snapshot_age_seconds",
            "Age of the latest runtime snapshot in seconds.",
            ["db_identifier"],
            registry=self._registry,
        )
        self._db_numbackends = Gauge(
            "pg_monitor_runtime_db_numbackends",
            "Number of backends from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=self._registry,
        )
        self._db_xact_commit = Gauge(
            "pg_monitor_runtime_db_xact_commit",
            "Transactions committed from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=self._registry,
        )
        self._db_xact_rollback = Gauge(
            "pg_monitor_runtime_db_xact_rollback",
            "Transactions rolled back from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=self._registry,
        )
        self._db_blks_read = Gauge(
            "pg_monitor_runtime_db_blks_read",
            "Blocks read from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=self._registry,
        )
        self._db_blks_hit = Gauge(
            "pg_monitor_runtime_db_blks_hit",
            "Blocks hit from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=self._registry,
        )
        self._db_deadlocks = Gauge(
            "pg_monitor_runtime_db_deadlocks",
            "Deadlocks from pg_stat_database.",
            ["db_identifier", "datname"],
            registry=self._registry,
        )

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
        self._clear_gauges()

        for state in states:
            labels = {"db_identifier": state.db_identifier}
            self._active_connections.labels(**labels).set(
                state.active_connections
            )
            self._blocked_sessions.labels(**labels).set(state.blocked_sessions)
            self._longest_tx.labels(**labels).set(
                state.longest_tx_duration_s or 0.0
            )
            self._waiting_locks.labels(**labels).set(state.waiting_locks)
            self._granted_locks.labels(**labels).set(state.granted_locks)
            self._snapshot_age.labels(**labels).set(
                max((observed_at - state.captured_at).total_seconds(), 0.0)
            )

            for db in state.database:
                db_labels = {
                    "db_identifier": state.db_identifier,
                    "datname": db.datname,
                }
                self._db_numbackends.labels(**db_labels).set(db.numbackends)
                self._db_xact_commit.labels(**db_labels).set(db.xact_commit)
                self._db_xact_rollback.labels(**db_labels).set(
                    db.xact_rollback
                )
                self._db_blks_read.labels(**db_labels).set(db.blks_read)
                self._db_blks_hit.labels(**db_labels).set(db.blks_hit)
                self._db_deadlocks.labels(**db_labels).set(db.deadlocks)

        return generate_latest(self._registry).decode("utf-8")

    def _clear_gauges(self) -> None:
        self._active_connections.clear()
        self._blocked_sessions.clear()
        self._longest_tx.clear()
        self._waiting_locks.clear()
        self._granted_locks.clear()
        self._snapshot_age.clear()
        self._db_numbackends.clear()
        self._db_xact_commit.clear()
        self._db_xact_rollback.clear()
        self._db_blks_read.clear()
        self._db_blks_hit.clear()
        self._db_deadlocks.clear()


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
