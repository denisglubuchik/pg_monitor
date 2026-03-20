from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pg_monitor.storage import StorageError, StorageUnitOfWorkFactory

from .errors import CollectorConnectionError, CollectorError
from .service import collect_queries_once, collect_runtime_once

if TYPE_CHECKING:
    from pg_monitor.collector.repository import AsyncpgCollectorRepository
    from pg_monitor.config import CollectorSettings

logger = logging.getLogger("pg_monitor.collector.scheduler")


class CollectorScheduler:
    def __init__(
        self,
        settings: CollectorSettings,
        repository: AsyncpgCollectorRepository,
        storage_uow_factory: StorageUnitOfWorkFactory,
    ) -> None:
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._repository = repository
        self._storage_uow_factory = storage_uow_factory
        self._started = False

    async def start(self) -> None:
        if self._started:
            return

        await self._preflight_dependencies()

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

        self._scheduler.shutdown(wait=True)
        self._scheduler.remove_all_jobs()
        self._started = False

        logger.info(
            "collector_scheduler_stopped",
            extra={
                "component": "collector",
            },
        )

    async def _run_runtime_job(self) -> None:
        try:
            snapshot = await asyncio.wait_for(
                collect_runtime_once(self._repository),
                timeout=self._settings.runtime_job_timeout_seconds,
            )
            async with self._storage_uow_factory() as uow:
                rows_written = (
                    await uow.runtime_snapshots.write_runtime_snapshot(snapshot)
                )
        except CollectorError:
            logger.warning(
                "collector_runtime_job_failed",
                extra={
                    "component": "collector",
                    "collection_profile": "runtime",
                },
            )
            return
        except StorageError:
            logger.warning(
                "collector_runtime_snapshot_write_failed",
                extra={
                    "component": "collector",
                    "collection_profile": "runtime",
                },
            )
            return
        except TimeoutError:
            logger.warning(
                "collector_runtime_job_timeout",
                extra={
                    "component": "collector",
                    "collection_profile": "runtime",
                    "timeout_s": self._settings.runtime_job_timeout_seconds,
                },
            )
            return

        logger.info(
            "collector_runtime_job_completed",
            extra={
                "component": "collector",
                "collection_profile": "runtime",
                "db_identifier": snapshot.db_identifier,
                "rows_written": rows_written,
            },
        )

    async def _run_queries_job(self) -> None:
        try:
            snapshot = await asyncio.wait_for(
                collect_queries_once(self._repository),
                timeout=self._settings.query_job_timeout_seconds,
            )
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
        except TimeoutError:
            logger.warning(
                "collector_queries_job_timeout",
                extra={
                    "component": "collector",
                    "collection_profile": "queries",
                    "timeout_s": self._settings.query_job_timeout_seconds,
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

    async def _preflight_dependencies(self) -> None:
        try:
            await self._repository.ping()
        except CollectorError:
            raise

        try:
            async with self._storage_uow_factory() as uow:
                await uow.runtime_snapshots.list_runtime_current()
        except StorageError as exc:
            raise CollectorConnectionError(
                f"collector storage preflight failed: {exc}"
            ) from exc
