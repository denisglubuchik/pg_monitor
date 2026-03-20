from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from typing import TYPE_CHECKING

from dishka import make_async_container

from pg_monitor.config import (
    CollectorSettings,
    load_collector_settings,
    resolve_settings_paths,
)
from pg_monitor.logging import configure_logging
from pg_monitor.providers.collector import CollectorProvider

from .errors import CollectorConnectionError
from .scheduler import CollectorScheduler

logger = logging.getLogger("pg_monitor.collector.worker")

if TYPE_CHECKING:
    from dishka.async_container import AsyncContainer


def run() -> None:
    asyncio.run(run_worker())


async def run_worker(
    settings: CollectorSettings | None = None,
    *,
    stop_event: asyncio.Event | None = None,
) -> None:
    worker_settings = settings or _load_runtime_settings()
    configure_logging(
        level=worker_settings.log_level,
        service=worker_settings.app_name,
        environment=worker_settings.environment,
    )

    if not worker_settings.collector_scheduler_enabled:
        logger.info(
            "collector_worker_disabled",
            extra={
                "component": "collector",
            },
        )
        return

    local_stop_event = stop_event or asyncio.Event()
    if stop_event is None:
        _register_signal_handlers(local_stop_event)

    container: AsyncContainer | None = None
    scheduler: CollectorScheduler | None = None
    try:
        (
            container,
            scheduler,
        ) = await _build_and_start_scheduler_with_retry(worker_settings)

        logger.info(
            "collector_worker_started",
            extra={
                "component": "collector",
            },
        )

        await local_stop_event.wait()
    finally:
        if scheduler is not None:
            await scheduler.shutdown()
        if container is not None:
            await _close_container(container)
        logger.info(
            "collector_worker_stopped",
            extra={
                "component": "collector",
            },
        )


def _load_runtime_settings() -> CollectorSettings:
    env_path = resolve_settings_paths()
    return load_collector_settings(env_path=env_path)


def _register_signal_handlers(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)


async def _build_and_start_scheduler_with_retry(
    settings: CollectorSettings,
) -> tuple[AsyncContainer, CollectorScheduler]:
    delay = settings.collector_startup_retry_base_delay_seconds
    max_attempts = settings.collector_startup_retry_attempts
    max_delay = settings.collector_startup_retry_max_delay_seconds

    for attempt in range(1, max_attempts + 1):
        container: AsyncContainer | None = None
        scheduler: CollectorScheduler | None = None
        try:
            container = make_async_container(CollectorProvider(settings))
            scheduler = await container.get(CollectorScheduler)
            await scheduler.start()
            return container, scheduler
        except CollectorConnectionError as exc:
            if container is not None:
                await _close_container(container)

            if attempt >= max_attempts:
                logger.exception(
                    "collector_scheduler_startup_failed",
                    extra={
                        "component": "collector",
                        "error_type": exc.__class__.__name__,
                    },
                )
                raise

            logger.warning(
                "collector_scheduler_start_retry attempt=%s/%s retry_in_s=%.1f",
                attempt,
                max_attempts,
                delay,
                extra={
                    "component": "collector",
                    "error_type": exc.__class__.__name__,
                },
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)

    msg = "collector scheduler startup retry loop exhausted unexpectedly"
    raise RuntimeError(msg)


async def _close_container(container: AsyncContainer) -> None:
    await container.close()
