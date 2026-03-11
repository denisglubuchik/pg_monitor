from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pg_monitor.storage import StorageError, StorageUnitOfWorkFactory

from .errors import CollectorError
from .service import collect_queries_once, collect_runtime_once

if TYPE_CHECKING:
    from pg_monitor.collector.repository import AsyncpgCollectorRepository
    from pg_monitor.config import CollectorSettings

logger = logging.getLogger("pg_monitor.collector.scheduler")


class CollectorScheduler:
    def __init__(self, settings: CollectorSettings) -> None:
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._repository: AsyncpgCollectorRepository | None = None
        self._storage_uow_factory: StorageUnitOfWorkFactory | None = None
        self._started = False

    def bind_dependencies(
        self,
        repository: AsyncpgCollectorRepository,
        storage_uow_factory: StorageUnitOfWorkFactory,
    ) -> None:
        self._repository = repository
        self._storage_uow_factory = storage_uow_factory

    async def start(self) -> None:
        if self._started:
            return
        if self._repository is None or self._storage_uow_factory is None:
            msg = "collector scheduler dependencies are not initialized"
            raise RuntimeError(msg)

        self._scheduler.add_job(
            self._run_runtime_job,
            trigger="interval",
            seconds=self._settings.runtime_poll_interval_seconds,
            id="collector_runtime",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=self._settings.runtime_poll_interval_seconds,
            next_run_time=datetime.now(UTC),
        )
        self._scheduler.add_job(
            self._run_queries_job,
            trigger="interval",
            seconds=self._settings.query_poll_interval_seconds,
            id="collector_queries",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=self._settings.query_poll_interval_seconds,
            next_run_time=datetime.now(UTC),
        )
        self._scheduler.start()
        self._started = True

        logger.info(
            "collector_scheduler_started",
            extra={
                "component": "collector",
                "runtime_interval_s": (
                    self._settings.runtime_poll_interval_seconds
                ),
                "query_interval_s": self._settings.query_poll_interval_seconds,
            },
        )

    async def shutdown(self) -> None:
        if not self._started:
            return

        self._scheduler.shutdown(wait=False)
        self._scheduler.remove_all_jobs()
        self._started = False

        logger.info(
            "collector_scheduler_stopped",
            extra={
                "component": "collector",
            },
        )

    async def _run_runtime_job(self) -> None:
        if self._repository is None:
            return

        try:
            snapshot = await collect_runtime_once(self._repository)
        except CollectorError:
            logger.warning(
                "collector_runtime_job_failed",
                extra={
                    "component": "collector",
                    "collection_profile": "runtime",
                },
            )
            return

        logger.info(
            "collector_runtime_job_completed",
            extra={
                "component": "collector",
                "collection_profile": "runtime",
                "db_identifier": snapshot.db_identifier,
            },
        )

    async def _run_queries_job(self) -> None:
        if self._repository is None or self._storage_uow_factory is None:
            return

        try:
            snapshot = await collect_queries_once(self._repository)
            async with self._storage_uow_factory() as uow:
                rows_written = await uow.query_snapshots.write_query_snapshot(
                    snapshot
                )
        except CollectorError:
            logger.warning(
                "collector_queries_job_failed",
                extra={
                    "component": "collector",
                    "collection_profile": "queries",
                },
            )
            return
        except StorageError:
            logger.warning(
                "collector_query_snapshot_write_failed",
                extra={
                    "component": "collector",
                    "collection_profile": "queries",
                },
            )
            return

        logger.info(
            "collector_queries_job_completed",
            extra={
                "component": "collector",
                "collection_profile": "queries",
                "db_identifier": snapshot.db_identifier,
                "rows_written": rows_written,
            },
        )
