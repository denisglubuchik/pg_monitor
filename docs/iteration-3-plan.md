# План итерации 3

## Статус

В работе (обновлено 2026-03-11).

Реализовано на текущий момент:
- storage-модуль + Alembic migration для `query_metric_snapshots`;
- collector write-path для query snapshot в storage DB;
- API endpoints:
  - `/analytics/queries/weekly-top`;
  - `/analytics/queries/week-over-week`;
- docker baseline:
  - `docker/compose/compose.yaml`;
  - единый PostgreSQL инстанс с двумя БД;
  - сервис `migrator` (`alembic upgrade head`);
- unit и API-тесты, интеграционные тесты запускаются флагом `--run-integration`.

## Зафиксированные решения

1. Retention в итерации 3 не делаем (откладывается на отдельный этап).
2. В `docker compose` итерации 3 поднимаем один PostgreSQL-инстанс с разными БД:
- target DB (мониторимая);
- storage DB (service snapshot storage).
3. В итерации 3 сохраняем только query snapshot из `pg_stat_statements`.
4. Runtime-метрики (`pg_stat_activity`, `pg_locks`, `pg_stat_database`) не сохраняем в storage на этом этапе; их развитие переносим в итерацию 4.
5. Для storage используем SQLAlchemy ORM (async), не только Core.
6. В итерации 3 реализуем оба query analytics endpoint:
- weekly top;
- week-over-week compare.

## Название

Snapshot storage + delta analytics за период + Docker baseline.

Связанная архитектура: `docs/iteration-3-architecture.md`.

## Цель итерации

Собрать первый полезный аналитический контур MVP:
- collector не только читает `pg_stat_*`, но и сохраняет query snapshot в отдельное storage-хранилище;
- сервис считает корректные дельты за период (`t_start` -> `t_end`);
- есть API/use-case для weekly analytics и сравнения "эта неделя vs предыдущая";
- инфраструктура запуска локально в Docker, с отдельной папкой `docker/`.

## Scope итерации

1. Docker baseline (первый этап итерации):
- завести отдельную папку `docker/` под артефакты контейнеризации;
- добавить Dockerfile приложения;
- добавить `docker compose` профиль для локального запуска API + collector + одного PostgreSQL-инстанса с двумя БД (target + storage).

2. Storage слой snapshot (query metrics only):
- добавить `storage` модуль;
- реализовать запись query snapshot пакетно;
- хранить снимки в отдельной service DB (не в мониторимой БД);
- добавить ORM-модели и миграции схемы через Alembic.

3. Query delta analytics за период:
- реализовать расчет дельт по счетчикам между двумя точками времени;
- учесть сброс счетчиков (`pg_stat_statements_reset`, restart): отрицательные дельты не пропускать в ответ;
- реализовать агрегации top queries by total time / calls за период.

4. API/use-case аналитики:
- endpoint/use-case weekly analytics;
- endpoint/use-case сравнения "эта неделя vs предыдущая";
- валидация параметров окна, лимитов и сортировки.

5. Конфигурация:
- добавить настройки storage DB (`PG_MONITOR_STORAGE_DSN` и related tuning);
- обновить `.env.example`.

6. Тесты:
- unit-тесты на формулу дельт (включая reset cases);
- unit-тесты storage repository;
- integration-тест: запись snapshot -> расчет дельт -> API-ответ по периоду.

## Out of Scope

1. Prometheus endpoint `/metrics` и exporter-логика (итерация 4).
2. Полный compose-стек observability (Prometheus/Grafana/Alertmanager/Loki/Promtail) из итерации 6.
3. Финальные dashboards и alert rules (итерация 5).
4. Расширение аналитики beyond weekly compare (ad-hoc BI, сложные percentile-отчеты).

## Definition of Ready (перед кодом)

1. Согласован формат Docker baseline для итерации 3:
- какие сервисы поднимаем в `docker compose` сейчас;
- какие оставляем на итерацию 6.
2. Согласована схема хранения snapshot (таблицы, индексы, PK/unique).
3. Согласована формула дельт при возможном reset счетчиков.
4. Согласованы окна сравнения периодов:
- timezone (рекомендуемо UTC);
- границы недели (ISO week).
5. Согласован контракт API аналитики (поля ответа, сортировки, лимиты).

## Детальный план работ

1. Подготовить Docker-каркас (первый шаг).
- Создать структуру в `docker/`;
- добавить Dockerfile и compose-файл для локального запуска;
- проверить запуск API/collector в контейнерах.

2. Зафиксировать контракты storage и analytics (до реализации).
- DTO для snapshot row и результата period analytics;
- интерфейс repository для чтения/записи snapshot;
- контракт API ответов weekly analytics.

3. Написать тесты (до реализации).
- unit: delta calculator (обычный кейс, reset, пустая база, неполные окна);
- unit: маппинг storage rows <-> domain models;
- integration: end-to-end путь "collector snapshot -> storage -> analytics API".

4. Реализовать storage слой.
- модуль `src/pg_monitor/storage/` (ORM entities + repositories + models);
- миграции Alembic;
- пакетная запись `QuerySnapshotResult.statements` в storage DB.

5. Интегрировать storage в collector flow.
- после `collect_queries_once` добавлять write snapshot;
- structured logging для write-цикла (`rows_written`, `duration_ms`, `db_identifier`).

6. Реализовать analytics service + API.
- сервис расчета дельт и top queries за период;
- weekly compare сервис;
- API endpoints с валидацией входных параметров.

7. Локальная проверка.
- `uv run ruff check`;
- `uv run pytest -q`;
- smoke-check docker сценария через `docker compose up`.

## Критерии готовности (Definition of Done)

1. Query snapshot (`pg_stat_statements`) стабильно сохраняются в отдельной storage DB.
2. Дельты по `total_exec_time` и `calls` за период считаются корректно.
3. API weekly analytics и compare endpoint возвращают ожидаемые top queries.
4. Unit + integration тесты зеленые.
5. Docker артефакты для локального запуска (в отдельной папке `docker/`) документированы и работают.
6. Обновлены README и `.env.example` под новый контур.

## Артефакты итерации

1. Модули `storage` и `query_analytics` в `src/pg_monitor/`.
2. Миграции Alembic для snapshot storage.
3. API endpoints аналитики периода.
4. Docker артефакты в папке `docker/`.
5. Набор unit + integration тестов для storage/delta/API.
6. Обновленная документация запуска и конфигурации.

## Риски и меры

1. Риск: неверная дельта при reset счетчиков.
Мера: явная логика обработки reset + unit-тесты на негативные/аномальные дельты.

2. Риск: рост объема snapshot и деградация запросов аналитики.
Мера: индексы по `captured_at/queryid/db_identifier`, ограничение `limit`.

3. Риск: усложнение docker-сценария до полного стека раньше времени.
Мера: в итерации 3 держать только минимальный runtime-контур; observability stack оставить на итерацию 6.

## Открытые вопросы на согласование

Открытых вопросов нет.
