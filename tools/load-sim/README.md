# Load Simulation Scripts

Скрипты для ручной генерации нагрузки на локальном docker-стенде.

## Требования

1. Поднят compose-стек из `docker/compose/compose.yaml`.
2. Доступен `docker compose` на хосте.

## Быстрый сценарий

```bash
./tools/load-sim/setup.sh
./tools/load-sim/query-burst.sh 1000
./tools/load-sim/http-burst.sh 300
```

Потом смотри:
- Prometheus: `http://localhost:9090`;
- Grafana: `http://localhost:3000`;
- API analytics: `http://localhost:8000/analytics/queries/weekly-top?db_identifier=monitored_db`.

## Lock contention (blocked sessions)

В первом терминале:

```bash
./tools/load-sim/lock-holder.sh 300
```

Во втором терминале (пока первый не завершился):

```bash
./tools/load-sim/lock-waiter.sh
```

Это создаст ожидание блокировки, которое видно в runtime-метриках и алертах.

## Скрипты

- `setup.sh` — включает `pg_stat_statements`, создает служебные таблицы;
- `query-burst.sh [iterations]` — SQL-нагрузка на `monitored_db`;
- `http-burst.sh [requests] [base_url]` — HTTP-нагрузка на API;
- `lock-holder.sh [sleep_seconds]` — удерживает row lock;
- `lock-waiter.sh` — пытается взять тот же lock и ждет освобождения.
