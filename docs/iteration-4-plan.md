# План итерации 4

## Статус

План подготовлен (2026-03-11), реализация не начата.

Связанная архитектура: `docs/iteration-4-architecture.md`.

## Название

Prometheus `/metrics` + runtime storage read-model + завершение resilience.

## Цель итерации

Довести MVP до рабочего runtime observability контура:
1. collector сохраняет runtime snapshot в storage;
2. API отдает `GET /metrics` в формате Prometheus;
3. runtime-пайплайн устойчив к временным сбоям зависимостей.

## Что уже есть (не делать повторно)

1. Разделение API и collector процессов.
2. Query analytics через storage (`weekly-top`, `week-over-week`).
3. Scheduler safety baseline (`max_instances=1`, `coalesce=True`).
4. Worker shutdown и startup retry/backoff каркас.

## Scope итерации

1. Runtime storage слой:
- ORM-модели для runtime history + current tables;
- Alembic migration;
- repository для записи runtime snapshot и чтения current-state.

2. API `/metrics`:
- новый роут;
- runtime metrics service + exporter;
- Prometheus exposition text.

3. Collector integration:
- runtime job записывает runtime snapshot в storage;
- структурированные логи write-path.

4. Resilience hardening:
- preflight dependency checks перед стартом scheduler;
- job-level timeout для runtime/query jobs;
- корректная деградация при частичных отказах.

5. Тесты:
- unit, API, integration для нового runtime metrics контура.

6. Docker compose расширение:
- добавить сервис `prometheus` в `docker/compose/compose.yaml`;
- добавить минимальный `prometheus.yml` для scrape `api:8000/metrics`;
- проверить локальный сценарий `api + collector + postgres + migrator + prometheus`.

## Out of Scope

1. Grafana dashboards и Alertmanager rules (итерация 5).
2. Loki/Promtail и полный observability compose-стек (итерация 6).
3. Retention/архивация runtime history.
4. Расширенная аналитика runtime history в API (кроме `/metrics`).

## Архитектурные решения (фиксируем)

1. Runtime пишется в storage, API не ходит напрямую в target PostgreSQL.
2. Храним два уровня данных:
- history (`runtime_snapshots`, `runtime_database_snapshots`);
- current read model (`runtime_current`, `runtime_database_current`).
3. `/metrics` читает только current read model.
4. Экспортируем runtime-метрики минимум с label `db_identifier`,
для `pg_stat_database` добавляем label `datname`.
5. `GET /healthz` остается liveness-only (без тяжелых проверок зависимостей).
6. В итерации 4 подключаем только Prometheus как scrape consumer для `/metrics`,
без Grafana/Alertmanager/Loki.

## Definition of Ready

1. Согласован финальный набор runtime таблиц и их индексов.
2. Согласован список метрик `/metrics` и labels.
3. Согласовано поведение при устаревшем snapshot:
- метрика `runtime_snapshot_age_seconds` обязательна;
- stale данные не считаются ошибкой endpoint.
4. Согласованы timeout-значения jobs и поведение при timeout.

## Детальный план реализации

1. Подготовка схемы storage.
- Добавить ORM сущности runtime history/current.
- Добавить dataclass DTO runtime state в `storage.models`.
- Добавить Alembic migration.

2. Расширение repository и UoW.
- Реализовать `RuntimeSnapshotRepository`:
  - insert history runtime snapshot;
  - insert history database rows;
  - upsert current runtime row;
  - upsert current runtime database rows.
- Добавить `runtime_snapshots` property в `StorageUnitOfWork`.
- Обновить exports в `storage.__init__`.

3. Интеграция collector runtime write-path.
- В `CollectorScheduler._run_runtime_job` после `collect_runtime_once`
  открыть UoW и вызвать runtime repository write.
- Добавить structured логи:
  - `collector_runtime_snapshot_write_succeeded`;
  - `collector_runtime_snapshot_write_failed`.

4. Resilience hardening.
- Добавить preflight checks в `CollectorScheduler.start`:
  - проверка соединения с target DB (через repository call);
  - проверка соединения с storage DB (через короткий UoW read/write smoke).
- Добавить timeout обертку вокруг runtime/query jobs.
- Развести обработку `CollectorError`, `StorageError`, `TimeoutError`
  в разные log event types.

5. Runtime metrics service и exporter.
- Добавить пакет `runtime_metrics`:
  - модели runtime state;
  - сервис чтения current-state из storage;
  - exporter в Prometheus text format.
- Выбрать стратегию:
  - либо `prometheus_client.CollectorRegistry` + `generate_latest`,
  - либо ручная генерация exposition (предпочтительно первый вариант).
- Добавить dependency `prometheus-client` в `pyproject.toml`.

6. API `/metrics`.
- Добавить `src/pg_monitor/api/metrics.py`.
- Подключить роут в `api/__init__.py`.
- Добавить DI provider для runtime metrics service в `providers/api.py`.
- Обработать `db_identifier` query param (optional filter).

7. Тесты и проверка.
- Unit:
  - runtime repository write/read;
  - exporter output (имена метрик, labels, content type).
- API:
  - `/metrics` возвращает 200 и prometheus payload;
  - фильтрация по `db_identifier`;
  - отсутствие данных -> валидный пустой/минимальный exposition.
- Integration:
  - collector runtime snapshot write -> `/metrics` возвращает это состояние.
- Smoke:
  - `uv run ruff check`;
  - `uv run pytest -q`;
  - `uv run pytest -q --run-integration` (при доступном docker).

8. Docker compose (Prometheus).
- Добавить конфиг `docker/prometheus/prometheus.yml`:
  - `scrape_interval: 15s`;
  - target: `api:8000`.
- Обновить `docker/compose/compose.yaml` сервисом `prometheus`:
  - image `prom/prometheus`;
  - mount `prometheus.yml`;
  - port `9090:9090`;
  - `depends_on: api`.
- Обновить `docker/README.md` и root `README.md` командами запуска
  и quick-check scrape status.

## Критерии готовности (Definition of Done)

1. Runtime snapshot стабильно пишется в storage на каждом runtime poll.
2. `GET /metrics` отдает корректный Prometheus exposition и покрыт тестами.
3. При временной недоступности target/storage БД collector продолжает работу
по retry/backoff стратегии, не падая процессом.
4. Query analytics API не деградирует после добавления runtime контура.
5. Alembic migration применима и откатываема.
6. Документация (`README`, roadmap, iteration docs) синхронизирована.
7. `docker compose up --build` поднимает `prometheus`, и таргет `api`
в `UP` состоянии на странице `/targets`.

## План по этапам (внутри итерации)

1. Этап A: Storage schema + repository + unit tests.
2. Этап B: Collector runtime write-path + resilience hardening.
3. Этап C: Runtime metrics service + `/metrics` API + API tests.
4. Этап D: Integration tests + документация + финальная валидация.
5. Этап E: Prometheus в compose + smoke-check scrape.

## Риски и меры

1. Риск: высокая кардинальность labels в `/metrics`.
Мера: ограничиваем labels до `db_identifier` и `datname`, без query-level labels.

2. Риск: несогласованность history/current при частичном падении транзакции.
Мера: write runtime snapshot и upsert current выполнять в одной транзакции UoW.

3. Риск: startup retry сейчас не ловит часть реальных ошибок.
Мера: явные preflight checks перед scheduler start.

4. Риск: рост размера history таблиц.
Мера: retention вне scope итерации, но фиксируем как follow-up задачу.

5. Риск: `/metrics` недоступен в момент старта Prometheus.
Мера: `depends_on` + readiness retry со стороны Prometheus scrape.

## Артефакты итерации

1. `src/pg_monitor/runtime_metrics/*`.
2. Изменения `storage` (ORM, repositories, models, UoW).
3. Новый API роут `/metrics`.
4. Alembic migration runtime-таблиц.
5. Тесты unit/API/integration для runtime metrics контура.
6. Обновленные `docs/roadmap.md`, `README.md`, architecture docs.
7. `docker/prometheus/prometheus.yml` + обновленный `docker/compose/compose.yaml`.
