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
	@echo "  make load-setup             - prepare monitored_db for load simulation"
	@echo "  make load-query             - run SQL query burst"
	@echo "  make load-http              - run HTTP burst against API"
	@echo "  make load-lock-holder       - hold row lock (run in one terminal)"
	@echo "  make load-lock-waiter       - wait on row lock (run in another terminal)"
	@echo ""
	@echo "Variables:"
	@echo "  QUERY_ITERATIONS=$(QUERY_ITERATIONS)"
	@echo "  HTTP_REQUESTS=$(HTTP_REQUESTS)"
	@echo "  BASE_URL=$(BASE_URL)"
	@echo "  LOCK_SECONDS=$(LOCK_SECONDS)"
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
	./tools/load-sim/setup.sh

load-query:
	./tools/load-sim/query-burst.sh $(QUERY_ITERATIONS)

load-http:
	./tools/load-sim/http-burst.sh $(HTTP_REQUESTS) $(BASE_URL)

load-lock-holder:
	./tools/load-sim/lock-holder.sh $(LOCK_SECONDS)

load-lock-waiter:
	./tools/load-sim/lock-waiter.sh

# Treat extra make goals as service names (for example: make logs api).
$(SERVICES):
	@:
