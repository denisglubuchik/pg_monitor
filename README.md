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

## Минимум для дашбордов

1. Overview:
   - active connections
   - deadlocks
   - blocked sessions
   - longest transaction
2. Query Analytics (за период):
   - top queries by total time (delta за период)
   - top by calls
   - latency динамика
   - эта неделя vs предыдущая
3. Logs panel (Loki):
   - ошибки/таймауты/lock wait рядом с метриками

## Алерты MVP

- высокая средняя latency запросов
- blocked sessions
- long transaction выше порога
- рост deadlocks
- высокая утилизация соединений

## Статус

Текущий статус (2026-03-17):
- Итерация 1 завершена.
- Итерация 2 завершена:
  - реализован collector (`pg_stat_*`);
  - API и collector вынесены в отдельные процессы;
  - добавлены split settings (`ApiSettings` / `CollectorSettings`);
  - добавлен startup retry/backoff для collector worker.
- Итерация 3 завершена:
  - реализованы storage (`SQLAlchemy ORM`) + миграции (`Alembic`);
  - реализованы endpoint'ы query analytics:
    - `GET /analytics/queries/weekly-top`;
    - `GET /analytics/queries/week-over-week`;
  - collector сохраняет query snapshots в storage DB;
  - локальный docker-профиль обновлен:
    - один `PostgreSQL` инстанс с двумя БД;
    - отдельный сервис `migrator` с `alembic upgrade head`.
- Итерация 4 завершена:
  - реализован runtime storage path для `/metrics`;
  - реализован endpoint `GET /metrics` (runtime + service metrics);
  - в docker compose добавлен `prometheus` для scrape API;
  - добавлены preflight checks и job timeouts в collector scheduler.
- Итерация 5 завершена:
  - добавлены инфраструктурные конфиги для `Alertmanager` и `Grafana`;
  - добавлены Prometheus alert rules (`docker/prometheus/alerts.yml`);
  - добавлен provisioning dashboards/datasources для Grafana;
  - добавлены и стабилизированы dashboards:
    - `Overview v2` (runtime + lock + TPS/cache/rollback signals, переменные `db_identifier`/`datname`);
    - `Query Analytics` (SQL-based top queries + window coverage из storage DB);
  - endpoint'ы query analytics расширены параметрами окна:
    - `window_start_at`;
    - `window_end_at`;
  - Telegram routing переведен на env-only конфигурацию:
    - секреты не хранятся в `docker/alertmanager/alertmanager.yml`;
    - значения `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` подставляются в runtime при старте `alertmanager`;
  - локальный compose smoke-check пройден (`make up`, `make ps`, readiness Alertmanager, проверка `Prometheus -> Alertmanager`);
  - детальный план: `docs/iteration-5-plan.md`.

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

## Документация

- Полная спецификация MVP: `docs/mvp-spec.md`
- Архитектурное предложение: `docs/architecture.md`
- Пошаговый roadmap MVP: `docs/roadmap.md`
- Детальный план итерации 3: `docs/iteration-3-plan.md`
- Архитектура итерации 3: `docs/iteration-3-architecture.md`
- Детальный план итерации 4: `docs/iteration-4-plan.md`
- Архитектура итерации 4: `docs/iteration-4-architecture.md`
- Детальный план итерации 5: `docs/iteration-5-plan.md`
- Архитектура итерации 5: `docs/iteration-5-architecture.md`
- Корреляция логов: `docs/logging-correlation.md`
- Правила совместной работы: `docs/working-agreement.md`

## Quick Start (на текущем этапе)

```bash
uv sync
export PG_MONITOR_PG_DSN='postgresql://user:password@localhost:5432/postgres'
# API процесс:
uv run uvicorn pg_monitor.app:create_app --factory --host 0.0.0.0 --port 8000
# Collector worker процесс:
uv run pg-monitor-collector
```

Локальный docker-профиль (итерации 3-5):

```bash
make up
```

После запуска:
- API: `http://localhost:8000`
- Prometheus: `http://localhost:9090` (`Status -> Targets` для проверки scrape)
- Alertmanager: `http://localhost:9093`
- Grafana: `http://localhost:3000` (`admin/admin`)

Быстрые проверки локального стека:

```bash
make ps
curl -fsS http://localhost:9093/-/ready
curl -fsS http://localhost:9090/api/v1/alertmanagers
```

Текущий источник данных для панелей:
- `Overview` читает Prometheus runtime/service метрики.
- `Query Analytics` таблицы читают storage PostgreSQL datasource (`pg_monitor_storage`).
- ссылки `Weekly Top API (fixed 7d)` и `Week over Week API (fixed 7d)` на dashboard используются как API quick links.

Набор скриптов для ручной генерации нагрузки:
- `tools/load-sim/README.md`
- быстрый старт: `./tools/load-sim/setup.sh && ./tools/load-sim/query-burst.sh 1000`

## Тесты

Быстрый запуск (без интеграционных тестов):

```bash
pytest -q
```

Интеграционные тесты запускаются только явно:

```bash
pytest -q --run-integration
```

## Конфиг (.env + env)

Приоритет источников:
`defaults < .env < OS env`.

Готовые шаблоны:
- `.env.example`

Обязательный параметр:
- `PG_MONITOR_PG_DSN` (в `.env` или OS env)
- `PG_MONITOR_STORAGE_DSN` (в `.env` или OS env)

Ключевые параметры collector:
- `PG_MONITOR_RUNTIME_POLL_INTERVAL_SECONDS`
- `PG_MONITOR_QUERY_POLL_INTERVAL_SECONDS`
- `PG_MONITOR_COLLECTOR_STARTUP_RETRY_ATTEMPTS`
- `PG_MONITOR_COLLECTOR_STARTUP_RETRY_BASE_DELAY_SECONDS`
- `PG_MONITOR_COLLECTOR_STARTUP_RETRY_MAX_DELAY_SECONDS`

Параметры alerting:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Важно по безопасности:
- не храните Telegram token/chat_id в `docker/alertmanager/alertmanager.yml` и в git;
- `docker/alertmanager/alertmanager.yml` используется как шаблон, значения подставляются в runtime из env при старте `alertmanager`.

## Ключевой механизм “за период”

`pg_stat_statements` хранит накопленные счетчики.
Чтобы получить честные метрики за произвольный период, используем:

1. регулярные снапшоты,
2. выбор `t_start` и `t_end`,
3. расчет дельт между снапшотами.

## Принципы реализации

- Небольшие итерации.
- Сначала тесты, потом код.
- Без overengineering.
- Каждая фича: план -> согласование -> реализация.
- Все неясности уточняются до начала реализации.
- Все ключевые решения согласуются до внесения изменений.
