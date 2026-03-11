# Архитектура итерации 2

## Цель

Определить технический дизайн collector-слоя для надежного чтения `pg_stat_*` с разной частотой сбора:
- runtime-метрики часто;
- query-метрики реже, чтобы снизить нагрузку на БД.

## Границы итерации

Входит:
- чтение данных из PostgreSQL;
- нормализация в модели;
- раздельные результаты runtime/query-профилей.

Не входит:
- долговременное хранение snapshot;
- расчет дельт между snapshot;
- публикация в `/metrics`.

## Предлагаемая структура модулей

```text
src/pg_monitor/
  collector/
    __init__.py
    models.py          # DTO/domain-модели snapshot
    queries.py         # SQL шаблоны для pg_stat_* источников
    repository.py      # низкоуровневый DB access на asyncpg
    service.py         # orchestration collect_runtime_once / collect_queries_once
    errors.py          # доменные исключения collector-слоя
    scheduler.py       # APScheduler orchestration
    worker.py          # отдельный процесс collector worker
```

## Разделение процессов

1. API и collector запускаются отдельными процессами.
2. API-процесс:
- FastAPI endpoints (`/healthz`, далее `/metrics`).
3. Collector-процесс:
- scheduler + DB polling.
4. Это исключает дублирование polling job при запуске API с несколькими worker-процессами.

## Контракт результата цикла

1. `collect_runtime_once()` возвращает:

- `captured_at: datetime` (UTC, единая для всех секций)
- `db_identifier: str`
- `activity: ActivitySnapshot`
- `locks: LocksSnapshot`
- `database: list[DatabaseMetric]`

2. `collect_queries_once()` возвращает:

- `captured_at: datetime` (UTC)
- `db_identifier: str`
- `statements: list[StatementMetric]`

Это позволяет в следующей итерации независимо сохранять runtime и query snapshot.

## Polling-профиль

- runtime-профиль: `60` секунд.
- query-профиль: `900` секунд (15 минут).
- Оба интервала конфигурируемые через env:
  - `PG_MONITOR_RUNTIME_POLL_INTERVAL_SECONDS`;
  - `PG_MONITOR_QUERY_POLL_INTERVAL_SECONDS`.

## Split конфигов

1. `ApiSettings`:
- `app_name`, `environment`, `log_level`, `host`, `port`.
2. `CollectorSettings`:
- `app_name`, `environment`, `log_level`,
- `pg_dsn`,
- `collector_scheduler_enabled`,
- `runtime_poll_interval_seconds`,
- `query_poll_interval_seconds`,
- `collector_startup_retry_*`.

## Модели данных (минимум для MVP)

1. `StatementMetric`
- `queryid: str`
- `dbid: int`
- `userid: int`
- `query: str`
- `calls: int`
- `total_exec_time_ms: float`
- `mean_exec_time_ms: float`
- `rows: int`
- `shared_blks_hit/read/dirtied/written: int`

2. `ActivitySnapshot`
- `active_connections: int`
- `blocked_sessions: int`
- `longest_tx_duration_s: float | None`

3. `LocksSnapshot`
- `waiting_locks: int`
- `granted_locks: int`

4. `DatabaseMetric`
- `datid: int`
- `datname: str`
- `numbackends: int`
- `xact_commit: int`
- `xact_rollback: int`
- `blks_read: int`
- `blks_hit: int`
- `deadlocks: int`

## Поток выполнения `collect_runtime_once`

1. Сгенерировать `poll_cycle_id`, зафиксировать `captured_at = now(UTC)`.
2. Проверить доступность соединения.
3. Выполнить 3 SQL-блока (`activity`, `locks`, `database`).
4. Преобразовать строки в typed-модели.
5. Вернуть `RuntimeSnapshotResult`.
6. Записать structured logs:
- `collector_cycle_started` (`collection_profile=runtime`)
- `collector_cycle_succeeded` (`collection_profile=runtime`)
- `collector_cycle_failed` (`collection_profile=runtime`)

## Поток выполнения `collect_queries_once`

1. Сгенерировать `poll_cycle_id`, зафиксировать `captured_at = now(UTC)`.
2. Проверить доступность соединения и наличие `pg_stat_statements`.
3. Выполнить SQL по `pg_stat_statements`.
4. Преобразовать строки в `StatementMetric`.
5. Вернуть `QuerySnapshotResult`.
6. Записать structured logs:
- `collector_cycle_started` (`collection_profile=queries`)
- `collector_cycle_succeeded` (`collection_profile=queries`)
- `collector_cycle_failed` (`collection_profile=queries`)

## Подход к ошибкам

- Ошибки коннекта/таймаутов -> `CollectorConnectionError`.
- Ошибки SQL/схемы -> `CollectorQueryError`.
- Отсутствие обязательного extension (`pg_stat_statements`) -> `CollectorPrerequisiteError`.

Верхний слой получает typed-исключение и может применить retry/backoff в итерации 4.

## SQL-стратегия

1. `pg_stat_statements`:
- ограничить набор полей до MVP-минимума;
- включать `query` text;
- собирать реже отдельным циклом.

2. `pg_stat_activity`:
- агрегирующий запрос для `active_connections`, `blocked_sessions`, `longest_tx_duration_s`.

3. `pg_locks`:
- агрегирующий запрос по `granted`/`waiting`.

4. `pg_stat_database`:
- собирать по всем БД, исключая шаблонные при необходимости.

## Тестовая стратегия

1. Unit-тесты:
- маппинг строк в модели;
- обработка `NULL`/пустых наборов;
- консистентность `captured_at`.

2. Integration-тест:
- PostgreSQL контейнер;
- `CREATE EXTENSION pg_stat_statements`;
- выполнение набора SQL;
- проверка, что `collect_queries_once()` возвращает non-empty `statements` с `query`;
- проверка, что `collect_runtime_once()` возвращает валидные агрегаты.

## Зафиксированные технические решения

1. DB-драйвер: `asyncpg`.
2. Формат `queryid`: строка для стабильной сериализации между источниками.
3. `query` text хранится в `StatementMetric` и в snapshot-хранилище следующей итерации.
4. Сбор разделен на два цикла (runtime/query), чтобы снизить нагрузку на мониторимую БД.
5. Scheduler вынесен в отдельный worker-процесс.
6. Для startup worker используется встроенный retry/backoff.

## Подход к storage DB (следующая итерация)

1. Snapshot хранятся в отдельной service DB, не в мониторимой БД.
2. Для доступа к storage DB использовать SQLAlchemy Core (async) + `asyncpg` драйвер.
3. Полноценную ORM-модель не использовать на старте:
- запись snapshot идет пакетно и проще/быстрее через Core insert;
- меньше риска накладных расходов и скрытой магии ORM на high-volume вставках.
4. Миграции схемы вести через Alembic.
