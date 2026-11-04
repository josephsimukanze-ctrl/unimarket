.PHONY: help up down backend frontend migrate makemigrations test lint shell

help:
	@echo "make up            Start Postgres + Redis"
	@echo "make down          Stop containers"
	@echo "make backend       Run Django dev server"
	@echo "make frontend      Run Vite dev server"
	@echo "make migrate       Apply migrations"
	@echo "make makemigrations Create migrations"
	@echo "make test          Run backend tests"
	@echo "make shell         Django shell"

up:
	cd infra/docker && docker compose up -d
	@echo "Postgres and Redis started."

down:
	cd infra/docker && docker compose down

backend:
	cd backend && uv run python manage.py runserver 0.0.0.0:8001

frontend:
	cd frontend && pnpm dev

migrate:
	cd backend && uv run python manage.py migrate

makemigrations:
	cd backend && uv run python manage.py makemigrations

test:
	cd backend && uv run pytest

shell:
	cd backend && uv run python manage.py shell
