# Logging Correlation (MVP)

## Цель

Сделать быстрый путь расследования: от ошибки/пика метрик к конкретному запросу и циклу сбора.

## Корреляционные поля

1. `request_id`
- Контекст HTTP-запроса к exporter.
- Берется из `X-Request-ID` или генерируется middleware.

2. `poll_cycle_id`
- Идентификатор цикла polling.
- Назначается в коде poller перед сбором snapshot.

3. `queryid`
- Идентификатор SQL-запроса из `pg_stat_statements`.
- Добавляется в события по аналитике/аномалиям.

## Минимальный формат JSON-события

Обязательные поля:
- `timestamp`
- `level`
- `logger`
- `message`
- `service`
- `env`
- `component`
- `request_id`
- `poll_cycle_id`
- `queryid`
- `duration_ms`
- `error_type`

Дополнительно для HTTP:
- `method`
- `path`
- `status_code`

## Правило для Loki

В labels хранить только низкую кардинальность:
- `service`
- `env`
- `component`

Поля `request_id`, `poll_cycle_id`, `queryid` хранить в JSON-пейлоаде лога.

## Что уже реализовано

1. Middleware проставляет `request_id` и возвращает `X-Request-ID` в ответе.
2. Structured logging пишет контекстные поля (`request_id`, `poll_cycle_id`, `queryid`) в JSON.
3. Есть базовые тесты на middleware и контекст форматтера.

