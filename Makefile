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

monitoring-up:
	docker compose -f docker-compose.monitoring.yml up -d
monitoring-down:
	docker compose -f docker-compose.monitoring.yml down
monitoring-logs:
	docker compose -f docker-compose.monitoring.yml logs -f --tail=100
monitoring-smoke:
	bash scripts/smoke_test_monitoring.sh