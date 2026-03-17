FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

COPY pyproject.toml uv.lock README.md alembic.ini ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY alembic ./alembic
COPY main.py main_collector.py ./
RUN uv sync --frozen --no-dev

RUN chown -R app:app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

USER app

FROM base AS api
CMD ["uv", "run", "--no-dev", "--frozen", "uvicorn", "pg_monitor.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["uv", "run", "--no-dev", "--frozen", "pg-monitor-collector"]

FROM base AS migrator
CMD ["uv", "run", "--no-dev", "--frozen", "alembic", "upgrade", "head"]
