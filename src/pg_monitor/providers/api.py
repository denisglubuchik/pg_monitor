from __future__ import annotations

from collections.abc import AsyncIterator  # noqa: TC003

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (  # noqa: TC002
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from pg_monitor.config import ApiSettings  # noqa: TC001
from pg_monitor.metrics import (
    RuntimeMetricsExporter,
    RuntimeMetricsService,
    ServiceMetrics,
)
from pg_monitor.query_analytics import QueryAnalyticsService
from pg_monitor.storage import (
    StorageUnitOfWorkFactory,
    create_storage_engine,
    create_storage_session_factory,
)


class AppProvider(Provider):
    def __init__(self, settings: ApiSettings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def provide_api_settings(self) -> ApiSettings:
        return self._settings

    @provide(scope=Scope.APP)
    async def provide_storage_engine(
        self,
        settings: ApiSettings,
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
    def provide_storage_uow_factory(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> StorageUnitOfWorkFactory:
        return StorageUnitOfWorkFactory(session_factory)

    @provide(scope=Scope.APP)
    def provide_query_analytics_service(
        self,
        uow_factory: StorageUnitOfWorkFactory,
    ) -> QueryAnalyticsService:
        return QueryAnalyticsService(uow_factory)

    @provide(scope=Scope.APP)
    def provide_runtime_metrics_service(
        self,
        uow_factory: StorageUnitOfWorkFactory,
    ) -> RuntimeMetricsService:
        return RuntimeMetricsService(uow_factory)

    @provide(scope=Scope.APP)
    def provide_service_metrics(self) -> ServiceMetrics:
        return ServiceMetrics()

    @provide(scope=Scope.APP)
    def provide_runtime_metrics_exporter(
        self,
        service_metrics: ServiceMetrics,
    ) -> RuntimeMetricsExporter:
        return RuntimeMetricsExporter(service_metrics)
