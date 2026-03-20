# pg-monitor

Сервис мониторинга и анализа PostgreSQL-запросов за период + визуализация и алертинг.

## MVP стек

- FastAPI exporter
- Prometheus
- Grafana
- Alertmanager
- Loki + Promtail

## Что делает система (MVP)

1. Забирает статистику из `pg_stat_statements`, `pg_stat_activity`, `pg_locks`, `pg_stat_database`.
2. Периодически сохраняет снапшоты query-метрик.
3. Считает метрики за выбранный период (например, 7 дней) по дельтам.
4. Публикует технические метрики через `/metrics` для Prometheus.
5. Отдает endpoint `/healthz` для проверки состояния.
6. Визуализирует метрики и query analytics в Grafana.
7. Отправляет алерты через Alertmanager (в т.ч. в Telegram).
8. Собирает логи в Loki для расследования инцидентов.

## Основная ценность MVP

- Анализ запросов во времени, а не только “текущие графики”.
- Топ дорогих запросов за период.
- Динамика деградации и рост блокировок/долгих транзакций.
- Быстрый переход от проблем на графике к конкретному `queryid` и логам.

## Запуск
### Docker compose (полный стек observability)

```bash
make up
```

После запуска:
- API: `http://localhost:8000`
- Prometheus: `http://localhost:9090` (`Status -> Targets` для проверки scrape)
- Alertmanager: `http://localhost:9093`
- Loki: `http://localhost:3100/ready`
- Grafana: `http://localhost:3000` (`admin/admin`)

Быстрые проверки локального стека:

```bash
make ps
curl -fsS http://localhost:9093/-/ready
curl -fsS http://localhost:9090/api/v1/alertmanagers
curl -fsS http://localhost:3100/ready
```

## Query Analytics API

`GET /analytics/queries/weekly-top`
- обязательные параметры:
  - `db_identifier`
- опциональные параметры:
  - `limit` (default `20`)
  - `sort_by` (`total_exec_time_ms_delta` или `calls_delta`)
  - `window_start_at` (ISO datetime)
  - `window_end_at` (ISO datetime)
- поведение:
  - если `window_start_at/window_end_at` не переданы, используется дефолтное окно последних 7 дней;
  - если передан только один параметр окна, возвращается `422`.

`GET /analytics/queries/week-over-week`
- обязательные параметры:
  - `db_identifier`
- опциональные параметры:
  - `limit` (default `20`)
  - `sort_by` (`total_exec_time_ms_delta` или `calls_delta`)
  - `window_start_at` (ISO datetime)
  - `window_end_at` (ISO datetime)
- поведение:
  - если `window_start_at/window_end_at` не переданы, сравниваются 2 соседних окна по 7 дней;
  - если окно передано, `current_week` берется из переданного диапазона, `previous_week` строится как предыдущий диапазон той же длины;
  - если передан только один параметр окна, возвращается `422`.

Текущий источник данных для панелей:
- `Overview` читает Prometheus runtime/service метрики.
- `Query Analytics` таблицы читают storage PostgreSQL datasource (`pg_monitor_storage`).
- `Service Metrics` читает Prometheus + Loki и поддерживает drilldown `metrics -> Explore logs`.
- ссылки `Weekly Top API (fixed 7d)` и `Week over Week API (fixed 7d)` на dashboard используются как API quick links.

Набор скриптов для ручной генерации нагрузки:
- `tools/load-sim/README.md`
- быстрый старт: `./tools/load-sim/setup.sh && ./tools/load-sim/query-burst.sh 1000`
