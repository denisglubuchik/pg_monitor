# План итерации 2

## Статус

Завершена (2026-03-10).

## Название

PostgreSQL collector (`pg_stat_*`) + нормализация snapshot.

## Цель итерации

Подготовить слой сбора метрик из PostgreSQL как надежный источник данных для следующих итераций (storage, delta analytics, exporter):
- выполняются два типа цикла сбора:
  - runtime-цикл (`pg_stat_activity`, `pg_locks`, `pg_stat_database`) с baseline-интервалом 60 сек;
  - query-цикл (`pg_stat_statements` + `query` text) с интервалом 900 сек (15 минут);
- данные приводятся к единым Python-моделям snapshot;
- есть unit-тесты на нормализацию и минимум один integration test с PostgreSQL в testcontainers.

## Scope итерации

1. Модуль `collector` с SQL-запросами к `pg_stat_*`.
2. Модели snapshot (DTO/domain) для результатов сбора.
3. Сервис раздельного сбора:
- `collect_runtime_once`;
- `collect_queries_once`.
4. Обработка ошибок подключения/чтения с понятными исключениями и логированием.
5. Набор unit-тестов + минимум 1 integration test (testcontainers).

## Out of Scope

1. Периодическое расписание polling loop.
2. Долговременное хранилище snapshot.
3. Расчет дельт и weekly analytics API.
4. `/metrics` endpoint и Prometheus-интеграция.
5. Grafana/Alertmanager/Loki-compose.

## Definition of Ready (перед кодом)

1. Согласован финальный минимальный набор полей из каждого `pg_stat_*` источника.
2. Зафиксирована стратегия идентификации БД (`db_identifier`) для snapshot.
3. Зафиксирован polling-профиль:
- runtime-метрики: 60 сек;
- query-метрики: 900 сек (15 минут).
4. Зафиксированы конфиги интервалов:
- `PG_MONITOR_RUNTIME_POLL_INTERVAL_SECONDS`;
- `PG_MONITOR_QUERY_POLL_INTERVAL_SECONDS`.
5. Согласован подход к integration-тесту:
- контейнер PostgreSQL;
- включение `pg_stat_statements`;
- seed данных для проверки non-empty snapshot.
6. Нет открытых вопросов по API collector-слоя и формату моделей.

## Детальный план работ

1. Зафиксировать контракты collector-слоя.
Создать интерфейс/протокол доступа к БД и структуры результатов:
- `RuntimeSnapshotResult`;
- `QuerySnapshotResult`.
Добавить конфиги интервалов polling в settings.

2. Написать unit-тесты (до реализации).
Покрыть:
- маппинг SQL-строк в модели;
- корректные типы и default-значения;
- корректный `captured_at` в каждом профиле сбора;
- обработку пустых выборок.

3. Подготовить integration-тест (до реализации collector).
Поднять PostgreSQL через testcontainers, включить `pg_stat_statements`, выполнить тестовый SQL и проверить:
- `collect_runtime_once` возвращает валидные агрегаты;
- `collect_queries_once` возвращает записи с `queryid` и `query`.

4. Реализовать SQL collector.
Добавить запросы и адаптер данных для:
- `pg_stat_statements` (query metrics/counters),
- `pg_stat_activity` (активность/долгие транзакции),
- `pg_locks` (блокировки),
- `pg_stat_database` (агрегаты БД).

5. Реализовать сервис раздельного сбора.
Собрать два профиля результата и вернуть нормализованные структуры для дальнейшего storage.

6. Добавить structured logging событий цикла.
Логировать начало/успех/ошибку каждого цикла с `poll_cycle_id`, `db_identifier`, `duration_ms`, `collection_profile`.

7. Локальная проверка.
Прогнать `ruff` и `pytest`, отдельно проверить integration-тест.

## Критерии готовности (Definition of Done)

1. Unit-тесты на нормализацию snapshot проходят.
2. Минимум 1 integration test с testcontainers проходит стабильно.
3. `collect_runtime_once` и `collect_queries_once` формируют консистентные snapshot-структуры.
4. Ошибки подключения/SQL не приводят к немому падению: формируется понятная ошибка и structured log.
5. Документирован фактически реализованный контракт collector-слоя (модели + поля).
6. Интервалы polling задаются через конфиг и валидируются в settings.

## Артефакты итерации

1. Код модулей `collector` и моделей snapshot.
2. Набор unit + integration тестов для collector.
3. Краткая doc-спецификация контракта результата `collect_once`.

## Фактически реализовано

1. Реализован collector-слой:
- `collect_runtime_once`;
- `collect_queries_once`;
- typed ошибки (`CollectorConnectionError`, `CollectorQueryError`, `CollectorPrerequisiteError`).
2. Реализован отдельный worker-процесс для scheduler:
- API и collector запускаются раздельно.
3. Реализован split конфигов:
- `ApiSettings`;
- `CollectorSettings`.
4. Добавлен startup retry/backoff для запуска collector scheduler.
5. Усилен контроль качества данных:
- отсутствие обязательных полей в row больше не приводит к «тихим» нулям.
6. Логи дополнены контекстом scheduler-полей.
7. Тесты зелёные:
- unit;
- integration (testcontainers).

## Риски и меры

1. Риск: расхождения в доступности `pg_stat_statements` на разных инстансах.
Мера: явная проверка расширения и диагностическая ошибка с рекомендацией включения.

2. Риск: нестабильность integration-тестов с контейнером.
Мера: retry/ожидание readiness + фиксированные seed-шаги и таймауты.

3. Риск: высокий overhead из-за тяжелых SQL.
Мера: минимальный набор полей в MVP и ограничение объема выборок на старте.

## Открытые вопросы на согласование

1. В какой отдельной БД/схеме будут храниться snapshot в итерации 3?
2. Какой retention по snapshot нужен для MVP (30, 60, 90 дней)?
3. Какой минимум метрик обязателен для первого dashboard MVP (чтобы не тянуть лишние поля в collector)?
