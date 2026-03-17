from __future__ import annotations

from typing import Any, Mapping

import asyncpg

from .errors import CollectorConnectionError, CollectorQueryError
from .queries import (
    SQL_CHECK_PG_STAT_STATEMENTS,
    SQL_DB_IDENTIFIER,
    SQL_QUERY_STATEMENTS,
    SQL_RUNTIME_ACTIVITY,
    SQL_RUNTIME_DATABASE,
    SQL_RUNTIME_LOCKS,
)


def _connection_error_message(operation: str, exc: Exception) -> str:
    return f"collector connection failure during {operation}: {exc}"


def _query_error_message(operation: str, exc: Exception) -> str:
    return f"collector query failure during {operation}: {exc}"


async def create_pool(
    dsn: str,
    *,
    min_size: int = 1,
    max_size: int = 10,
    command_timeout: float = 30.0,
) -> asyncpg.Pool:
    try:
        return await asyncpg.create_pool(
            dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
        )
    except (OSError, asyncpg.PostgresConnectionError) as exc:
        raise CollectorConnectionError(
            _connection_error_message("pool creation", exc)
        ) from exc


class AsyncpgCollectorRepository:
    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        db_identifier: str | None = None,
    ) -> None:
        self._pool = pool
        self._db_identifier = db_identifier

    async def fetch_db_identifier(self) -> str:
        if self._db_identifier is not None:
            return self._db_identifier

        row = await self._fetch_row(
            SQL_DB_IDENTIFIER,
            operation="db_identifier",
        )
        db_name = str(row.get("db_name") or "unknown")
        host = str(row.get("host") or "unknown")
        port = int(row.get("port") or 0)
        return f"{db_name}@{host}:{port}"

    async def is_pg_stat_statements_available(self) -> bool:
        row = await self._fetch_row(
            SQL_CHECK_PG_STAT_STATEMENTS,
            operation="check_pg_stat_statements",
        )
        return bool(row.get("is_available"))

    async def fetch_activity_row(self) -> Mapping[str, Any]:
        return await self._fetch_row(SQL_RUNTIME_ACTIVITY, operation="activity")

    async def fetch_locks_row(self) -> Mapping[str, Any]:
        return await self._fetch_row(SQL_RUNTIME_LOCKS, operation="locks")

    async def fetch_database_rows(self) -> list[Mapping[str, Any]]:
        return await self._fetch_rows(
            SQL_RUNTIME_DATABASE,
            operation="database",
        )

    async def fetch_statement_rows(self) -> list[Mapping[str, Any]]:
        return await self._fetch_rows(
            SQL_QUERY_STATEMENTS,
            operation="query_statements",
        )

    async def _fetch_row(
        self,
        query: str,
        *,
        operation: str,
    ) -> Mapping[str, Any]:
        try:
            async with self._pool.acquire() as connection:
                row = await connection.fetchrow(query)
        except (OSError, asyncpg.PostgresConnectionError) as exc:
            raise CollectorConnectionError(
                _connection_error_message(operation, exc)
            ) from exc
        except asyncpg.PostgresError as exc:
            error_message = _query_error_message(operation, exc)
            raise CollectorQueryError(error_message) from exc

        if row is None:
            msg = f"collector query returned no rows during {operation}"
            raise CollectorQueryError(msg)
        return dict(row)

    async def _fetch_rows(
        self,
        query: str,
        *,
        operation: str,
    ) -> list[Mapping[str, Any]]:
        try:
            async with self._pool.acquire() as connection:
                rows = await connection.fetch(query)
        except (OSError, asyncpg.PostgresConnectionError) as exc:
            raise CollectorConnectionError(
                _connection_error_message(operation, exc)
            ) from exc
        except asyncpg.PostgresError as exc:
            error_message = _query_error_message(operation, exc)
            raise CollectorQueryError(error_message) from exc

        return [dict(row) for row in rows]
