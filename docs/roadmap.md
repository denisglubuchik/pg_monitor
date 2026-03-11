# MVP Roadmap (итерации)

## Текущий статус (на 2026-03-11)

- Итерация 1: завершена.
- Итерация 2: завершена.
- Итерация 3: в работе.
  - уже реализовано:
    - snapshot storage (ORM + Alembic),
    - query delta analytics service,
    - API endpoints `weekly-top` и `week-over-week`,
    - docker baseline с единым PostgreSQL и сервисом миграций.

## Обязательный процесс итерации

1. Детальный план итерации (согласование с владельцем проекта).
2. Уточнение всех неясностей до начала реализации.
3. Написание тестов.
4. Реализация кода.
5. Проверка критериев готовности и демонстрация результата.

Без выполнения шагов 1-2 итерация не начинается.

Формат каждой итерации:
- Что делаем
- Зачем
- Критерий готовности

## Итерация 1: FastAPI каркас + конфиг + structured logging

Что делаем:
- FastAPI каркас сервиса,
- settings loader: `defaults < .env < OS env`,
- валидация обязательных полей (включая DSN),
- json logging + log level + masking секретов.

Зачем:
- базовый runtime для exporter-сервиса.

Критерий готовности:
- unit-тесты на приоритет конфигов и masking проходят,
- сервис стартует, `/healthz` доступен.

## Итерация 2: PostgreSQL collector (pg_stat_*)

Что делаем:
- SQL-сбор из `pg_stat_statements`, `pg_stat_activity`, `pg_locks`, `pg_stat_database`,
- нормализация моделей snapshot,
- integration test с testcontainers postgres (минимум 1).

Зачем:
- получить достоверный первичный источник данных для анализа.

Критерий готовности:
- unit + integration тесты зелёные,
- один цикл сбора формирует консистентный snapshot.

Фактически реализовано:
- collector-слой на `asyncpg` для `pg_stat_statements`, `pg_stat_activity`, `pg_locks`, `pg_stat_database`;
- раздельные циклы сбора:
  - runtime-профиль;
  - queries-профиль;
- отдельный worker-процесс collector (не в API процессе);
- startup retry/backoff для worker;
- split конфигов на API и Collector settings;
- unit + integration тесты зелёные.

## Итерация 3: Snapshot storage + delta analytics за период

Детальный план: `docs/iteration-3-plan.md`.
Архитектура итерации: `docs/iteration-3-architecture.md`.

Что делаем:
- периодическое сохранение snapshot query-метрик,
- расчет дельт между `t_start` и `t_end`,
- API/use-case для weekly analytics и сравнения “эта неделя vs предыдущая”.

Зачем:
- ключевая ценность MVP: честный анализ за период, а не “за все время”.

Критерий готовности:
- корректно считаются top queries by total time/calls за период,
- есть тесты на расчет дельт и сравнение периодов.

## Итерация 4: Prometheus exporter + runtime resilience

Детальный план: `docs/iteration-4-plan.md`.
Архитектура итерации: `docs/iteration-4-architecture.md`.

Что делаем:
- endpoint `/metrics` (Prometheus),
- runtime snapshot storage (`runtime_*` tables + read model),
- интеграция runtime write-path в collector scheduler,
- добавление сервиса `prometheus` в локальный compose для scrape `/metrics`,
- hardening resilience (preflight checks, job timeouts, failure isolation),
- тесты endpoint’ов, runtime storage и оркестратора.

Зачем:
- надежная публикация runtime-техметрик в Prometheus через единый storage read-path.

Критерий готовности:
- `/metrics` отдает корректный Prometheus payload;
- runtime snapshot стабильно пишется в storage;
- collector устойчив к временным ошибкам target/storage БД;
- локальный Prometheus успешно скрейпит API endpoint `/metrics`.

## Итерация 5: Grafana dashboards + Alertmanager rules

Что делаем:
- dashboards:
  - Overview,
  - Query Analytics (period delta),
  - Logs panel (Loki),
- alert rules в Prometheus и routing через Alertmanager (Telegram).

Зачем:
- дать операционную видимость и уведомления в проде.

Критерий готовности:
- по заданным условиям алерты приходят в целевой канал,
- панели покрывают минимум из MVP-спека.

## Итерация 6: Loki + Promtail + compose

Что делаем:
- расширение docker-compose до полного observability-стека:
  - FastAPI exporter
  - Prometheus (уже добавлен в итерации 4)
  - Grafana
  - Alertmanager
  - Loki + Promtail
- runbook и quick start в README.

Зачем:
- полноценный локальный стенд для MVP-демо.

Критерий готовности:
- `docker compose up` поднимает весь стек,
- можно пройти путь: метрика -> алерт -> лог-корреляция.

## Контрольные точки согласования с тобой

1. После итерации 1: формат API и конфигов.
2. После итерации 2: финальный набор SQL-метрик и частота polling.
3. После итерации 3: формула дельт и окна сравнения периодов.
4. После итерации 5: финальные alert rules и dashboard panels.
