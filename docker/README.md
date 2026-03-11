# Docker Layout

Отдельная папка для Docker-артефактов проекта.

Реализованная структура (итерация 3):

```text
docker/
  README.md
  app/
    Dockerfile
  compose/
    compose.yaml
  env/
    .env.docker.example
  postgres/
    init/
      01-create-databases.sh
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
- `collector` (worker со scheduler).
