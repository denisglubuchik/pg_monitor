# Архитектура итерации 4

## Статус и цель

Дата актуализации: 2026-03-11.

Итерация 4 фокусируется на двух вещах:
1. Добавить production-пригодный `GET /metrics` в Prometheus формате.
2. Довести runtime-контур collector -> storage -> API до завершенного состояния.
3. Подключить Prometheus в локальный compose для scrape и smoke-валидации.

Важно: часть resilience уже реализована в итерации 2/3 (`max_instances=1`,
`coalesce=True`, graceful shutdown worker, startup retry/backoff). В этой
итерации не дублируем уже сделанное, а закрываем оставшиеся разрывы.

## Контекст текущей реализации

1. Collector уже умеет собирать runtime snapshot (`collect_runtime_once`),
но runtime snapshot пока не сохраняется в storage.
2. Query analytics путь уже работает через storage:
- collector writes query snapshots;
- API читает данные через `QueryAnalyticsService`.
3. Endpoint `/metrics` отсутствует.
4. Storage содержит только `query_metric_snapshots`.

## Ключевая проблема

API и collector разделены по процессам. Данные runtime в памяти collector
недоступны API процессу, поэтому `/metrics` не может строиться из in-memory
состояния worker.

## Архитектурное решение

1. Collector пишет runtime snapshot в storage.
2. API читает latest runtime state из storage и экспортирует в `/metrics`.
3. Для быстрого чтения `/metrics` используется current-state таблица
(`runtime_current`) с upsert по `db_identifier`.
4. Для диагностики и расширения храним историю runtime snapshots
(`runtime_snapshots`).
5. Prometheus скрейпит только API endpoint `/metrics`; сам collector
не экспонирует HTTP метрики напрямую.

## Принципы итерации

1. Один источник истины:
- storage DB хранит и query snapshots, и runtime state.

2. Чистые границы:
- collector: read target DB + write storage;
- API: read storage + HTTP exposition;
- роуты не содержат SQL и бизнес-агрегации.

3. Совместимость:
- не ломаем контракт query analytics (`weekly-top`, `week-over-week`);
- не встраиваем scheduler в API процесс.

## Целевая структура модулей

```text
src/pg_monitor/
  collector/
    scheduler.py
    service.py
  storage/
    orm.py                  # + Runtime* ORM entities
    models.py               # + Runtime DTOs for service layer
    repositories.py         # + RuntimeSnapshotRepository
    uow.py                  # + runtime_snapshots property
  runtime_metrics/
    __init__.py
    models.py               # RuntimeState, RuntimeDatabaseState
    service.py              # read latest runtime state from storage
    exporter.py             # runtime state -> Prometheus text/registry
  api/
    metrics.py              # GET /metrics
```

## Storage-модель runtime

### Таблица `runtime_snapshots`

Назначение: история для дебага и будущей аналитики.

Минимальные поля:
- `id` PK;
- `captured_at timestamptz not null`;
- `db_identifier text not null`;
- `active_connections bigint not null`;
- `blocked_sessions bigint not null`;
- `longest_tx_duration_s double precision null`;
- `waiting_locks bigint not null`;
- `granted_locks bigint not null`.

Индексы:
- (`db_identifier`, `captured_at`).

### Таблица `runtime_database_snapshots`

Назначение: состояние `pg_stat_database` по каждой БД на момент snapshot.

Минимальные поля:
- `runtime_snapshot_id` FK -> `runtime_snapshots.id`;
- `datid bigint not null`;
- `datname text not null`;
- `numbackends bigint not null`;
- `xact_commit bigint not null`;
- `xact_rollback bigint not null`;
- `blks_read bigint not null`;
- `blks_hit bigint not null`;
- `deadlocks bigint not null`.

Индекс:
- (`runtime_snapshot_id`, `datname`).

### Таблица `runtime_current`

Назначение: быстрый read-path для `/metrics` без поиска latest по истории.

Ключ:
- `db_identifier` PK.

Поля:
- `captured_at`;
- те же runtime-агрегаты, что в `runtime_snapshots`.

### Таблица `runtime_database_current`

Назначение: latest `pg_stat_database` по `db_identifier` + `datname`.

Ключ:
- (`db_identifier`, `datname`).

Поля:
- `captured_at`;
- `datid`, `numbackends`, `xact_commit`, `xact_rollback`,
  `blks_read`, `blks_hit`, `deadlocks`.

## Контракты слоев

### Storage port

- `write_runtime_snapshot(snapshot: RuntimeSnapshotResult) -> int`
  (возвращает количество записей в history/current суммарно или history rows;
  формат фиксируется в реализации и тестах).
- `get_runtime_current(db_identifier: str) -> RuntimeState | None`
- `list_runtime_current() -> list[RuntimeState]`

### Runtime metrics service

- `get_metrics_state(db_identifier: str | None) -> list[RuntimeState]`
  где `db_identifier=None` означает экспорт всех известных БД.

## API контур

1. `GET /healthz`
- остается liveness-check, без тяжёлых зависимостей.

2. `GET /metrics`
- `Content-Type: text/plain; version=0.0.4; charset=utf-8`;
- читает runtime current-state из storage;
- экспонирует runtime метрики + сервисные process-метрики.

Поддерживаемый query-param:
- `db_identifier` (опционально) для фильтрации конкретного target DB.

## Deployment контур (итерация 4)

`docker compose` профиль итерации 4 включает:
1. `postgres`
2. `migrator`
3. `api`
4. `collector`
5. `prometheus`

Prometheus конфиг:
- scrape job `pg_monitor_api`;
- target `api:8000`;
- path `/metrics`.

Это минимальный observability-контур итерации 4. Grafana, Alertmanager,
Loki/Promtail остаются на следующих итерациях.

## Набор метрик (MVP итерации 4)

Глобальные (label: `db_identifier`):
- `pg_monitor_runtime_active_connections` (gauge)
- `pg_monitor_runtime_blocked_sessions` (gauge)
- `pg_monitor_runtime_longest_tx_duration_seconds` (gauge)
- `pg_monitor_runtime_waiting_locks` (gauge)
- `pg_monitor_runtime_granted_locks` (gauge)
- `pg_monitor_runtime_snapshot_age_seconds` (gauge)

По базе данных (labels: `db_identifier`, `datname`):
- `pg_monitor_runtime_db_numbackends` (gauge)
- `pg_monitor_runtime_db_xact_commit` (gauge)
- `pg_monitor_runtime_db_xact_rollback` (gauge)
- `pg_monitor_runtime_db_blks_read` (gauge)
- `pg_monitor_runtime_db_blks_hit` (gauge)
- `pg_monitor_runtime_db_deadlocks` (gauge)

## Потоки данных

### Query path (без изменений)

1. `collect_queries_once`.
2. `QuerySnapshotRepository.write_query_snapshot`.
3. `QueryAnalyticsService` считает дельты.

### Runtime path (новое)

1. `collect_runtime_once`.
2. `RuntimeSnapshotRepository.write_runtime_snapshot`:
- insert в history;
- upsert в current таблицы.
3. API `/metrics`:
- `RuntimeMetricsService` читает current;
- exporter генерирует Prometheus exposition.

## Resilience: что закрываем в итерации 4

1. Startup preflight checks в scheduler start:
- явная проверка доступности target DB и storage DB до запуска jobs;
- retry/backoff должен ловить реальные connection failures.

2. Job-level timeouts:
- runtime/query jobs исполняются с ограничением времени;
- timeout логируется как отдельный тип ошибки.

3. Failure isolation:
- ошибка runtime write-path не останавливает query path;
- ошибка query write-path не останавливает runtime path.

4. Graceful shutdown:
- scheduler stop + закрытие контейнера/пулов без висящих задач.

## Почему этот вариант production-friendly

1. Нет межпроцессной зависимости через память.
2. `/metrics` читает предагрегированное current-state, а не тяжелые history
запросы.
3. History сохраняет диагностическую ценность для расследований.
4. Архитектура масштабируется без ломки контрактов API и collector.
5. Наличие Prometheus в compose позволяет проверить реальный scrape-путь
до перехода к dashboard/alerting этапам.
