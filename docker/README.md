# Docker Layout

Отдельная папка для Docker-артефактов проекта.

Реализованная структура (итерации 3-5):

```text
docker/
  README.md
  app/
    Dockerfile
  compose/
    compose.yaml
  env/
    .env.docker.example
  alertmanager/
    alertmanager.yml
  grafana/
    dashboards/
      overview.json
      query-analytics.json
    provisioning/
      dashboards/
        dashboards.yml
      datasources/
        datasources.yml
  postgres/
    init/
      01-create-databases.sh
  prometheus/
    alerts.yml
    prometheus.yml
```

Назначение:
- изолировать контейнерную инфраструктуру от `src/` и `tests/`;
- иметь отдельный compose-профиль для локальной разработки и проверки storage/delta-функциональности;
- подготовить базу для расширения к полному стеку в итерации 6.

Запуск:

```bash
cd docker/compose
docker compose up --build
```

Что поднимается:
- `postgres` (один PostgreSQL-инстанс с двумя БД: `monitored_db`, `pg_monitor_storage`);
- `migrator` (применяет `alembic upgrade head`);
- `api` (FastAPI);
- `collector` (worker со scheduler);
- `prometheus` (scrape `api:8000/metrics`, UI на `http://localhost:9090`);
- `alertmanager` (routing алертов, UI на `http://localhost:9093`);
- `grafana` (dashboards, UI на `http://localhost:3000`, `admin/admin`).

Telegram routing:
- заполните `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` в `docker/env/.env.docker.example` или в отдельном env-файле;
- Alertmanager читает переменные окружения и отправляет firing/resolved алерты через Bot API.

Ручная генерация нагрузки для проверки дашбордов/алертов:
- `./tools/load-sim/setup.sh`
- `./tools/load-sim/query-burst.sh 1000`
- `./tools/load-sim/lock-holder.sh 300` + `./tools/load-sim/lock-waiter.sh`
