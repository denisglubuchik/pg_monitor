# Load Simulation Scripts

Скрипты для ручной генерации нагрузки на локальном docker-стенде.
По умолчанию SQL-скрипты работают через `docker compose exec` и автоматически
ищут DB-сервис (`postgres`, `db`, `database` или похожее имя).
Для внешнего PostgreSQL можно задать `TARGET_PG_DSN` (тогда используется локальный `psql`).
Если авто-детект не подходит, можно указать `COMPOSE_DB_SERVICE`.

## Требования

1. Поднят compose-стек из `docker/compose/compose.yaml`.
2. Доступен `docker compose` на хосте.

## Быстрый сценарий

```bash
./tools/load-sim/setup.sh
./tools/load-sim/query-burst.sh 1000
./tools/load-sim/http-burst.sh 300 http://localhost:8000 monitored_db
```

Потом смотри:
- Prometheus: `http://localhost:9090`;
- Grafana: `http://localhost:3000`;
- API analytics: `http://localhost:8000/analytics/queries/weekly-top?db_identifier=monitored_db@postgres:5432`.

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
- `query-burst.sh [iterations] [target_db]` — SQL-нагрузка (по умолчанию `monitored_db`);
- `http-burst.sh [requests] [base_url] [target_db_or_db_identifier]` — HTTP-нагрузка на API;
- `lock-holder.sh [sleep_seconds] [target_db]` — удерживает row lock;
- `lock-waiter.sh [target_db]` — пытается взять тот же lock и ждет освобождения.

Пример для второй monitored БД:

```bash
./tools/load-sim/setup.sh monitored_db_2
./tools/load-sim/query-burst.sh 1000 monitored_db_2
./tools/load-sim/lock-holder.sh 120 monitored_db_2
./tools/load-sim/lock-waiter.sh monitored_db_2
./tools/load-sim/http-burst.sh 300 http://localhost:8000 monitored_db_2
```

Через `make`:

```bash
make load-query TARGET_DB=monitored_db_2
make load-http TARGET_DB=monitored_db_2
```

Внешний PostgreSQL (не локальный compose):

```bash
make load-setup TARGET_DB=my_db TARGET_PG_DSN='postgresql://user:pass@db.example.com:5432/postgres'
make load-query TARGET_DB=my_db TARGET_PG_DSN='postgresql://user:pass@db.example.com:5432/postgres' QUERY_ITERATIONS=500
make load-http TARGET_DB=my_db TARGET_DB_IDENTIFIER=my_db@db.example.com:5432 BASE_URL=https://api.example.com
```
