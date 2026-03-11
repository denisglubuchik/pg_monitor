# Architecture Proposal (MVP)

## Цель

Собрать MVP, который показывает не только текущее состояние PostgreSQL, но и query analytics за период на основе snapshot/delta.

## Компоненты MVP

- FastAPI API:
  - endpoints `/metrics`, `/healthz`.
- Collector worker:
  - polling PostgreSQL,
  - запись snapshot query-метрик,
  - расчет дельт за период.
- Prometheus:
  - scrape `/metrics`,
  - хранение технических time-series,
  - alert rules.
- Grafana:
  - overview dashboard,
  - query analytics dashboard,
  - logs panel (Loki datasource).
- Alertmanager:
  - маршрутизация алертов (в т.ч. Telegram).
- Loki + Promtail:
  - сбор и поиск логов PostgreSQL/exporter,
  - корреляция логов с пиками метрик.

## Логическая схема (MVP)

1. Collector worker запускает polling цикл(ы) по расписанию.
2. Collector читает `pg_stat_statements`, `pg_stat_activity`, `pg_locks`, `pg_stat_database`.
3. Snapshot writer сохраняет снимок метрик в локальное хранилище snapshot'ов.
4. Period analyzer считает дельты между `t_start` и `t_end` (например, 7 дней).
5. API публикует техметрики в `/metrics` и статус в `/healthz`.
6. Prometheus скрейпит `/metrics`, Grafana строит дашборды.
7. Alert rules срабатывают в Prometheus и отправляются через Alertmanager.
8. Loki/Promtail дают логи для расследования по queryid и времени.

## Слои сервиса

```text
src/pg_monitor/
  domain/      # модели snapshots, deltas, alerts
  config/      # env + file settings
  collector/   # SQL сбор из pg_stat_* views
  storage/     # snapshot repository
  services/    # polling, period analytics
  exporter/    # prometheus exposition
  api/         # fastapi endpoints (/metrics, /healthz)
  logging/     # structured logs for Loki
```

## Snapshot и расчеты за период

- В каждой итерации polling сохраняется snapshot:
  - `captured_at`,
  - `db_identifier`,
  - `queryid`,
  - counters из `pg_stat_statements` (calls, total_exec_time, rows, shared_blks_*).
- Метрики за период считаются как `delta = snapshot(t_end) - snapshot(t_start)`.
- Для дашбордов “эта неделя vs предыдущая” используются два окна с одинаковой длительностью.

## Минимальные панели

1. Overview:
   - active connections,
   - deadlocks,
   - blocked sessions,
   - longest transaction.
2. Query Analytics:
   - top by total time (delta),
   - top by calls,
   - latency trend,
   - this week vs previous week.
3. Logs:
   - ошибки/timeout/lock wait рядом с графиками.

## Алерты MVP

- высокая средняя latency,
- blocked sessions,
- long transaction > threshold,
- рост deadlocks,
- высокая утилизация connection pool.

## Варианты развития storage/read-model

Зафиксировано как общее архитектурное направление проекта:
1. Исторические snapshot-данные храним в PostgreSQL (`query` и `runtime` history).
2. `current` read-model для `/metrics` может быть вынесен в Redis для ускорения
read-path и снижения нагрузки на PostgreSQL.
3. При варианте с Redis:
- PostgreSQL остается источником истории и диагностики;
- Redis используется как hot current-state (`db_identifier`, `db_identifier+datname`);
- контракт `/metrics` и схема метрик не меняются.

Статус:
- в текущей итерации Redis не реализуется;
- это кандидат для отдельной итерации оптимизации runtime-контура.
