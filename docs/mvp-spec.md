# MVP Spec

## Проект

Сервис мониторинга и анализа PostgreSQL-запросов за период + визуализация и алертинг.

Стек:
- FastAPI exporter
- Prometheus
- Grafana
- Alertmanager
- Loki (+ Promtail)

## Что делает система

1. Забирает статистику запросов из PostgreSQL (`pg_stat_statements`, `pg_stat_activity`, `pg_locks`, `pg_stat_database`).
2. Периодически сохраняет снапшоты query-метрик, чтобы считать данные за выбранный период (например, 7 дней).
3. Публикует технические метрики через `/metrics` для Prometheus.
4. Визуализирует состояние БД и запросов в Grafana.
5. Отправляет алерты через Alertmanager (например, в Telegram).
6. Собирает логи (Postgres/exporter) в Loki для расследования инцидентов.

## Основная ценность MVP

- Топ самых дорогих запросов за неделю.
- Динамика деградации.
- Рост блокировок/долгих транзакций.
- Быстрый переход от проблемы на графике к конкретному `queryid` и контексту в логах.

## Компоненты MVP

- FastAPI API:
  - `/metrics`, `/healthz`.
- Collector worker:
  - опрос Postgres,
  - расчёт/хранение снапшотов.
- Prometheus:
  - сбор метрик,
  - alert rules.
- Grafana:
  - дашборды по БД и запросам.
- Alertmanager:
  - маршрутизация уведомлений.
- Loki + Promtail:
  - сбор и поиск логов,
  - корреляция с пиками метрик.

## Что показываем в дашбордах (минимум)

1. Overview:
   - active connections
   - deadlocks
   - blocked sessions
   - longest transaction
2. Query Analytics (за период):
   - top queries by total time (delta за период)
   - top by calls
   - latency динамика
   - сравнение “эта неделя vs предыдущая”
3. Logs panel (Loki):
   - ошибки/таймауты/lock wait рядом с метриками

## Алерты MVP

- высокая средняя latency запросов
- обнаружены blocked sessions
- long transaction > порога
- рост deadlocks
- высокая утилизация соединений

## Как считать “за неделю”

Ключевой механизм:
`pg_stat_statements` -> регулярные снапшоты -> дельты между `t_start` и `t_end`.

Это дает метрики за период, а не накопление “с начала жизни”.
