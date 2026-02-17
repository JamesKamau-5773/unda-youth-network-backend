.PHONY: help monitoring-up monitoring-down monitoring-ps monitoring-logs monitoring-restart open-prometheus open-grafana docs-check-no-emoji
.PHONY: test-postgres test-postgres-down

# Monitoring ports (host -> container)
# Prometheus: 19090 -> 9090
# Grafana:    13000 -> 3000

help:
	@echo "Usage: make <target>"
	@echo "Targets: monitoring-up monitoring-down monitoring-ps monitoring-logs monitoring-restart open-prometheus open-grafana docs-check-no-emoji"

docs-check-no-emoji:
	@python3 scripts/check_docs_no_emoji.py

monitoring-up:
	sudo docker compose -f docker-compose.monitoring.yml up -d

monitoring-down:
	sudo docker compose -f docker-compose.monitoring.yml down

monitoring-ps:
	sudo docker compose -f docker-compose.monitoring.yml ps

monitoring-logs:
	sudo docker compose -f docker-compose.monitoring.yml logs -f prometheus

monitoring-restart: monitoring-down monitoring-up

open-prometheus:
	@python3 -m webbrowser "http://localhost:19090" || true

open-grafana:
	@python3 -m webbrowser "http://localhost:13000" || true

generate-traffic:
	@echo "Running traffic generator against local app..."
	@DEV_SECRET_KEY=$$DEV_SECRET_KEY python3 scripts/generate_traffic.py

generate-nonde-traffic:
	@echo "Running in-process non-dev end-to-end generator (test client)..."
	@python3 scripts/generate_nonde_traffic.py


test-postgres:
	@echo "Starting Postgres test container..."
	docker compose -f docker-compose.test.yml up -d postgres
	@echo "Waiting for Postgres to be ready..."
	@for i in `seq 1 30`; do pg_isready -h localhost -p 5432 -U postgres && break || sleep 1; done
	@echo "Running pytest against Postgres (SQLALCHEMY_DATABASE_URI exported for the command)"
	@SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@localhost:5432/unda_test pytest -q

test-postgres-down:
	@echo "Stopping Postgres test container and removing volumes..."
	docker compose -f docker-compose.test.yml down -v
