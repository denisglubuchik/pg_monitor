from __future__ import annotations

from collections.abc import AsyncIterator  # noqa: TC003

from asyncpg import Pool  # noqa: TC002
from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (  # noqa: TC002
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from pg_monitor.collector.repository import (
    AsyncpgCollectorRepository,
    create_pool,
)
from pg_monitor.config import CollectorSettings  # noqa: TC001
from pg_monitor.storage import (
    StorageUnitOfWorkFactory,
    create_storage_engine,
    create_storage_session_factory,
)


class CollectorProvider(Provider):
    def __init__(self, settings: CollectorSettings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def provide_collector_settings(self) -> CollectorSettings:
        return self._settings

    @provide(scope=Scope.APP)
    async def provide_pg_pool(
        self,
        settings: CollectorSettings,
    ) -> AsyncIterator[Pool]:
        pool = await create_pool(str(settings.pg_dsn))
        yield pool
        await pool.close()

    @provide(scope=Scope.APP)
    async def provide_storage_engine(
        self,
        settings: CollectorSettings,
    ) -> AsyncIterator[AsyncEngine]:
        engine = create_storage_engine(str(settings.storage_dsn))
        yield engine
        await engine.dispose()

    @provide(scope=Scope.APP)
    def provide_storage_session_factory(
        self,
        engine: AsyncEngine,
    ) -> async_sessionmaker[AsyncSession]:
        return create_storage_session_factory(engine)

    @provide(scope=Scope.APP)
    def provide_collector_repository(
        self,
        pool: Pool,
    ) -> AsyncpgCollectorRepository:
        return AsyncpgCollectorRepository(pool)

    @provide(scope=Scope.APP)
    def provide_storage_uow_factory(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> StorageUnitOfWorkFactory:
        return StorageUnitOfWorkFactory(session_factory)
