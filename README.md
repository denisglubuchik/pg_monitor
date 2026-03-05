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

Сейчас инициализирован проект (`uv init`) и подготовлена документация.
Реализация кода идёт итерациями, test-first и по согласованному плану.

## Документация

- Полная спецификация MVP: `docs/mvp-spec.md`
- Архитектурное предложение: `docs/architecture.md`
- Пошаговый roadmap MVP: `docs/roadmap.md`
- Корреляция логов: `docs/logging-correlation.md`
- Правила совместной работы: `docs/working-agreement.md`

## Quick Start (на текущем этапе)

```bash
uv sync
export PG_MONITOR_PG_DSN='postgresql://user:password@localhost:5432/postgres'
uv run python main.py
```

## Конфиг (.env + env)

Приоритет источников:
`defaults < .env < OS env`.

Готовые шаблоны:
- `.env.example`

Обязательный параметр:
- `PG_MONITOR_PG_DSN` (в `.env` или OS env)

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
