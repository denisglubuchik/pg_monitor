.PHONY: help up down restart ps logs lint test test-integration \
	load-setup load-query load-http load-lock-holder load-lock-waiter

COMPOSE_FILE := docker/compose/compose.yaml

KNOWN_TARGETS := help up down restart ps logs lint test test-integration \
	load-setup load-query load-http load-lock-holder load-lock-waiter
SERVICES := $(filter-out $(KNOWN_TARGETS),$(MAKECMDGOALS))

QUERY_ITERATIONS ?= 1000
HTTP_REQUESTS ?= 300
BASE_URL ?= http://localhost:8000
LOCK_SECONDS ?= 300
TARGET_DB ?= monitored_db
TARGET_PG_DSN ?=
COMPOSE_DB_SERVICE ?=
TARGET_DB_IDENTIFIER ?=
LOAD_HTTP_TARGET ?= $(if $(strip $(TARGET_DB_IDENTIFIER)),$(TARGET_DB_IDENTIFIER),$(TARGET_DB))

help:
	@echo "Available targets:"
	@echo "  make up                     - build and start full docker stack (detached)"
	@echo "  make down                   - stop and remove full docker stack"
	@echo "  make restart                - restart full docker stack"
	@echo "  make ps                     - show compose services status"
	@echo "  make logs                   - tail logs for all compose services"
	@echo "                               (or: make logs api)"
	@echo "  make lint                   - run ruff checks"
	@echo "  make test                   - run unit/API tests"
	@echo "  make test-integration       - run integration tests"
	@echo "  make load-setup             - prepare TARGET_DB for load simulation"
	@echo "  make load-query             - run SQL query burst (TARGET_DB)"
	@echo "  make load-http              - run HTTP burst against API (TARGET_DB)"
	@echo "  make load-lock-holder       - hold row lock in TARGET_DB (run in one terminal)"
	@echo "  make load-lock-waiter       - wait on row lock in TARGET_DB (run in another terminal)"
	@echo ""
	@echo "Variables:"
	@echo "  QUERY_ITERATIONS=$(QUERY_ITERATIONS)"
	@echo "  HTTP_REQUESTS=$(HTTP_REQUESTS)"
	@echo "  BASE_URL=$(BASE_URL)"
	@echo "  LOCK_SECONDS=$(LOCK_SECONDS)"
	@echo "  TARGET_DB=$(TARGET_DB)"
	@echo "  TARGET_PG_DSN=$(TARGET_PG_DSN)"
	@echo "  COMPOSE_DB_SERVICE=$(COMPOSE_DB_SERVICE)"
	@echo "  SERVICES are inferred from extra args, e.g. 'make logs api'"

up:
	docker compose -f $(COMPOSE_FILE) up --build -d $(SERVICES)

down:
	docker compose -f $(COMPOSE_FILE) down $(SERVICES)

restart: down up

ps:
	docker compose -f $(COMPOSE_FILE) ps $(SERVICES)

logs:
	docker compose -f $(COMPOSE_FILE) logs -f $(SERVICES)

lint:
	uv run ruff check

test:
	uv run pytest -q

test-integration:
	uv run pytest -q --run-integration

load-setup:
	TARGET_PG_DSN="$(TARGET_PG_DSN)" COMPOSE_DB_SERVICE="$(COMPOSE_DB_SERVICE)" ./tools/load-sim/setup.sh $(TARGET_DB)

load-query:
	TARGET_PG_DSN="$(TARGET_PG_DSN)" COMPOSE_DB_SERVICE="$(COMPOSE_DB_SERVICE)" ./tools/load-sim/query-burst.sh $(QUERY_ITERATIONS) $(TARGET_DB)

load-http:
	TARGET_DB="$(TARGET_DB)" TARGET_DB_IDENTIFIER="$(TARGET_DB_IDENTIFIER)" ./tools/load-sim/http-burst.sh $(HTTP_REQUESTS) $(BASE_URL) $(LOAD_HTTP_TARGET)

load-lock-holder:
	TARGET_PG_DSN="$(TARGET_PG_DSN)" COMPOSE_DB_SERVICE="$(COMPOSE_DB_SERVICE)" ./tools/load-sim/lock-holder.sh $(LOCK_SECONDS) $(TARGET_DB)

load-lock-waiter:
	TARGET_PG_DSN="$(TARGET_PG_DSN)" COMPOSE_DB_SERVICE="$(COMPOSE_DB_SERVICE)" ./tools/load-sim/lock-waiter.sh $(TARGET_DB)

# Treat extra make goals as service names (for example: make logs api).
$(SERVICES):
	@:
