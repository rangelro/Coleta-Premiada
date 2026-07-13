# Comandos para Docker Compose

up:
	docker compose up -d
build:
	docker compose build
down:
	docker compose down
down-vol:
	docker compose down -v
logs:
	docker compose logs -f --tail=100
stop:
	docker compose stop

# Comandos para Django

migrations:
	docker compose exec core python manage.py makemigrations
migrate:
	docker compose exec core python manage.py migrate
createsuperuser:
	docker compose exec core python manage.py createsuperuser
shell:
	docker compose exec core bash
shell-microservice:
	docker compose exec collection-microservice bash

# Comandos de Backup do PostgreSQL

db-backup:
	docker compose exec db-backup /scripts/backup.sh
db-restore:
	docker compose exec db-backup /scripts/restore.sh $(FILE)

# Comandos para CI

check:
	docker compose run --rm core python manage.py check
migrations-check:
	docker compose run --rm core python manage.py makemigrations --check --dry-run
migrate-check:
	docker compose run --rm core python manage.py migrate

# Comandos para Monitoramento
# O stack de monitoramento agora é centralizado em ../coleta-observability.
monitoring-up:
	docker compose -f ../coleta-observability/docker-compose.yml up -d
monitoring-down:
	docker compose -f ../coleta-observability/docker-compose.yml down
monitoring-logs:
	docker compose -f ../coleta-observability/docker-compose.yml logs -f --tail=100
monitoring-smoke:
	bash scripts/smoke_test_monitoring.sh

# Comandos de manutencao

maintenance-smoke:
	bash scripts/smoke_test_maintenance.sh

# Relatorio de monitoramento (Python)
# Requer: pip install psycopg2-binary
# Uso: make monitor-report ARGS="--json --output /tmp/report.json"
monitor-report:
	docker compose run --rm postgres-maintenance python3 /maintenance/monitoring_report.py $(ARGS)
