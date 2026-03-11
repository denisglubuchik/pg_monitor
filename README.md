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

Текущий статус (2026-03-11):
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

## Документация

- Полная спецификация MVP: `docs/mvp-spec.md`
- Архитектурное предложение: `docs/architecture.md`
- Пошаговый roadmap MVP: `docs/roadmap.md`
- Детальный план итерации 3: `docs/iteration-3-plan.md`
- Архитектура итерации 3: `docs/iteration-3-architecture.md`
- Детальный план итерации 4: `docs/iteration-4-plan.md`
- Архитектура итерации 4: `docs/iteration-4-architecture.md`
- Корреляция логов: `docs/logging-correlation.md`
- Правила совместной работы: `docs/working-agreement.md`

## Quick Start (на текущем этапе)

```bash
uv sync
export PG_MONITOR_PG_DSN='postgresql://user:password@localhost:5432/postgres'
# API процесс:
uv run uvicorn pg_monitor.app:create_app --factory --host 0.0.0.0 --port 8000 --log-config none
# Collector worker процесс:
uv run pg-monitor-collector
```

Локальный docker-профиль (итерации 3-4):

```bash
cd docker/compose
docker compose up --build
```

После запуска:
- API: `http://localhost:8000`
- Prometheus: `http://localhost:9090` (`Status -> Targets` для проверки scrape)

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

## Ключевой механизм “за неделю”

`pg_stat_statements` хранит накопленные счетчики.
Чтобы получить честные метрики за период, используем:

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
