from __future__ import annotations

import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Callable, Protocol
from uuid import uuid4

from pg_monitor.logging import reset_poll_cycle_id, set_poll_cycle_id

from .errors import (
    CollectorError,
    CollectorPrerequisiteError,
    CollectorQueryError,
)
from .models import (
    ActivitySnapshot,
    DatabaseMetric,
    LocksSnapshot,
    QuerySnapshotResult,
    RuntimeSnapshotResult,
    StatementMetric,
)

logger = logging.getLogger("pg_monitor.collector")


class CollectorRepository(Protocol):
    async def fetch_db_identifier(self) -> str: ...

    async def is_pg_stat_statements_available(self) -> bool: ...

    async def fetch_activity_row(self) -> dict[str, object]: ...

    async def fetch_locks_row(self) -> dict[str, object]: ...

    async def fetch_database_rows(self) -> list[dict[str, object]]: ...

    async def fetch_statement_rows(self) -> list[dict[str, object]]: ...


NowProvider = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def collect_runtime_once(
    repository: CollectorRepository,
    *,
    now_provider: NowProvider = _utc_now,
) -> RuntimeSnapshotResult:
    captured_at = now_provider()
    started = perf_counter()
    poll_cycle_id = uuid4().hex
    token = set_poll_cycle_id(poll_cycle_id)
    profile = "runtime"
    db_identifier = "unknown"

    logger.info(
        "collector_cycle_started",
        extra={
            "component": "collector",
            "collection_profile": profile,
        },
    )

    try:
        db_identifier = await repository.fetch_db_identifier()
        activity_row = await repository.fetch_activity_row()
        locks_row = await repository.fetch_locks_row()
        database_rows = await repository.fetch_database_rows()

        result = RuntimeSnapshotResult(
            captured_at=captured_at,
            db_identifier=db_identifier,
            activity=ActivitySnapshot.from_row(activity_row),
            locks=LocksSnapshot.from_row(locks_row),
            database=[
                DatabaseMetric.from_row(row) for row in database_rows
            ],
        )

        duration_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "collector_cycle_succeeded",
            extra={
                "component": "collector",
                "collection_profile": profile,
                "db_identifier": db_identifier,
                "duration_ms": duration_ms,
            },
        )
        return result
    except CollectorError as exc:
        _log_collector_failure(
            profile=profile,
            db_identifier=db_identifier,
            started=started,
            error_type=exc.__class__.__name__,
        )
        raise
    except Exception as exc:
        _log_collector_failure(
            profile=profile,
            db_identifier=db_identifier,
            started=started,
            error_type="CollectorQueryError",
        )
        raise CollectorQueryError("collector runtime cycle failed") from exc
    finally:
        reset_poll_cycle_id(token)


async def collect_queries_once(
    repository: CollectorRepository,
    *,
    now_provider: NowProvider = _utc_now,
) -> QuerySnapshotResult:
    captured_at = now_provider()
    started = perf_counter()
    poll_cycle_id = uuid4().hex
    token = set_poll_cycle_id(poll_cycle_id)
    profile = "queries"
    db_identifier = "unknown"

    logger.info(
        "collector_cycle_started",
        extra={
            "component": "collector",
            "collection_profile": profile,
        },
    )

    try:
        db_identifier = await repository.fetch_db_identifier()
        is_available = await repository.is_pg_stat_statements_available()
        if not is_available:
            msg = (
                "pg_stat_statements extension is required "
                "for query collection"
            )
            raise CollectorPrerequisiteError(msg)

        statement_rows = await repository.fetch_statement_rows()
        result = QuerySnapshotResult(
            captured_at=captured_at,
            db_identifier=db_identifier,
            statements=[
                StatementMetric.from_row(row) for row in statement_rows
            ],
        )

        duration_ms = int((perf_counter() - started) * 1000)
        logger.info(
            "collector_cycle_succeeded",
            extra={
                "component": "collector",
                "collection_profile": profile,
                "db_identifier": db_identifier,
                "duration_ms": duration_ms,
            },
        )
        return result
    except CollectorError as exc:
        _log_collector_failure(
            profile=profile,
            db_identifier=db_identifier,
            started=started,
            error_type=exc.__class__.__name__,
        )
        raise
    except Exception as exc:
        _log_collector_failure(
            profile=profile,
            db_identifier=db_identifier,
            started=started,
            error_type="CollectorQueryError",
        )
        raise CollectorQueryError("collector query cycle failed") from exc
    finally:
        reset_poll_cycle_id(token)


def _log_collector_failure(
    *,
    profile: str,
    db_identifier: str,
    started: float,
    error_type: str,
) -> None:
    duration_ms = int((perf_counter() - started) * 1000)
    logger.exception(
        "collector_cycle_failed",
        extra={
            "component": "collector",
            "collection_profile": profile,
            "db_identifier": db_identifier,
            "duration_ms": duration_ms,
            "error_type": error_type,
        },
    )
