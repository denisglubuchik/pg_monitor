from __future__ import annotations

from typing import TYPE_CHECKING, Self

from .repositories import QuerySnapshotRepository, RuntimeSnapshotRepository

if TYPE_CHECKING:
    from types import TracebackType

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class StorageUnitOfWorkFactory:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    def __call__(self) -> StorageUnitOfWork:
        return StorageUnitOfWork(self._session_factory)


class StorageUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    @property
    def query_snapshots(self) -> QuerySnapshotRepository:
        if self._session is None:
            msg = "unit of work is not entered"
            raise RuntimeError(msg)
        return QuerySnapshotRepository(self._session)

    @property
    def runtime_snapshots(self) -> RuntimeSnapshotRepository:
        if self._session is None:
            msg = "unit of work is not entered"
            raise RuntimeError(msg)
        return RuntimeSnapshotRepository(self._session)

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        del tb
        if self._session is None:
            return

        try:
            if exc_type is None:
                await self._session.commit()
            else:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None
