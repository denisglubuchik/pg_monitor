# Архитектура итерации 3

## Цель

Сделать понятный и расширяемый контур "query analytics за период":
- collector продолжает собирать runtime + query данные из PostgreSQL;
- в storage сохраняются только query snapshot (`pg_stat_statements`);
- API читает аналитику из отдельного сервисного слоя;
- runtime storage и exporter-часть переносятся в итерацию 4.

## Принципы

1. Разделение по ответственности:
- `collector` только собирает данные;
- `storage` только хранит/читает snapshot;
- `query_analytics` считает бизнес-метрики периода;
- `api` только HTTP-контракт.

2. Явные границы между слоями:
- зависимости направлены внутрь (API -> analytics -> storage);
- collector использует storage только для записи query snapshot;
- API не обращается к БД напрямую.

3. Минимум "магии":
- SQLAlchemy ORM 2.0 (async) + `asyncpg` драйвер;
- явные repository/DAO границы, без SQL в API-слое.
- Unit of Work для транзакционных границ чтения/записи.

## Целевая структура модулей

```text
src/pg_monitor/
  collector/
    scheduler.py
    service.py
    ...
  storage/
    __init__.py
    base.py              # DeclarativeBase
    session.py           # async session factory
    orm.py               # ORM entities (query/runtime snapshots)
    repositories.py      # QuerySnapshotRepository, RuntimeSnapshotRepository
    models.py            # typed DTO для сервисного слоя
  query_analytics/
    __init__.py
    models.py            # PeriodWindow, QueryDelta, WeeklyTopResult
    delta.py             # чистая логика расчета дельт
    service.py           # orchestration: read snapshots -> delta -> top
  api/
    health.py
    query_analytics.py   # HTTP endpoints для weekly analytics
```

Примечание по неймингу:
- вместо общего `analytics` лучше `query_analytics`, чтобы сразу было понятно, что это analytics именно query-слоя.

## Кто зависит от storage

1. Collector:
- использует storage для записи query snapshot после `collect_queries_once`.

2. API:
- не использует storage напрямую;
- API вызывает `query_analytics.service`, а тот уже работает со storage repository.

## Потоки данных

### 1) Collector write path

1. Scheduler запускает `collect_queries_once`.
2. Collector получает `QuerySnapshotResult`.
3. `storage.repositories.QuerySnapshotRepository` сохраняет batch snapshot в storage DB.
4. Логируется `snapshot_write_succeeded|failed`.

### 2) API read path

1. HTTP endpoint получает окно периода и лимит.
2. `query_analytics.service` запрашивает в storage снимки для `t_start` и `t_end`.
3. `query_analytics.delta` считает дельты по query key.
4. Service сортирует top N и возвращает DTO в API.
5. API сериализует ответ.

## Транзакционные границы (UoW)

- `StorageUnitOfWorkFactory` живет в `APP` scope.
- На каждый use-case создается новый `StorageUnitOfWork`:
  - открывается отдельная `AsyncSession`;
  - при успешном завершении выполняется `commit`;
  - при исключении выполняется `rollback`.
- Репозитории (`QuerySnapshotRepository`) привязаны к текущей session UoW.

Это позволяет использовать один и тот же подход как в API, так и в collector worker.

## Миграции схемы

- Схема storage управляется через Alembic.
- Runtime-код не делает `create_all`/`ensure_schema`.
- В docker-профиле итерации 3 миграции применяются отдельным сервисом `migrator` до старта API/collector.

## Что хранится в storage (итерация 3)

Только query counters из `pg_stat_statements`:
- `captured_at`
- `db_identifier`
- `queryid`
- `dbid`
- `userid`
- `query`
- `calls`
- `total_exec_time_ms`
- `rows`
- `shared_blks_*`

Runtime-агрегаты (active connections, locks, deadlocks и т.п.) в storage не пишем.

## Схема хранения (MVP)

Рекомендуемая ORM-сущность/таблица:
- `query_metric_snapshots`

Ключевые поля:
- `captured_at timestamptz not null`
- `db_identifier text not null`
- `queryid text not null`
- `dbid int not null`
- `userid int not null`
- `query text not null`
- counters (`calls`, `total_exec_time_ms`, `rows`, `shared_blks_*`)

Рекомендуемый уникальный ключ:
- (`captured_at`, `db_identifier`, `queryid`, `dbid`, `userid`)

Индексы:
- (`db_identifier`, `captured_at`)
- (`queryid`, `captured_at`)

## Контракты слоев

### Storage port (интерфейс)

- `write_query_snapshot(snapshot: QuerySnapshotResult) -> int`
- `get_latest_snapshot_at_or_before(ts, db_identifier) -> list[QuerySnapshotRow]`

### Query analytics port

- `get_weekly_top_queries(db_identifier, now, limit, sort_by) -> WeeklyTopResult`
- `get_period_top_queries(db_identifier, t_start, t_end, limit, sort_by) -> PeriodTopResult`

Где `sort_by` минимум:
- `total_exec_time_ms_delta`
- `calls_delta`

## Политика обработки reset счетчиков

Если `end_counter < start_counter` для конкретного query key:
- считаем, что был reset/restart;
- запись исключаем из top выдачи (или помечаем `reset_detected=true` в debug-полях).

Для MVP итерации 3 достаточно исключения из top.

## API итерации 3 (предлагаемый минимальный контракт)

Вариант 1 (минимальный и читаемый):
- `GET /analytics/queries/weekly-top?db_identifier=...&limit=20&sort_by=total_exec_time_ms_delta`

Вариант 2 (расширенный в этой же итерации):
- `GET /analytics/queries/week-over-week?db_identifier=...&limit=20&sort_by=total_exec_time_ms_delta`

Зафиксировано для итерации 3:
- реализуем `weekly-top`;
- реализуем `week-over-week`.

## Почему это production-friendly

1. Слои изолированы, тестируются независимо.
2. ORM дает единый язык моделей/миграций/связей, проще сопровождение командой.
3. API не тянет SQL в роуты.
4. Легко расширить:
- добавить runtime storage (итерация 4+);
- добавить новые аналитические витрины без переписывания collector;
- заменить storage backend с минимальным влиянием на API.
