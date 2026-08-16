.PHONY: up down logs migrate test lint fmt shell

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f api

migrate:
	docker compose run --rm migrate

test:
	pytest -q

lint:
	ruff check .

fmt:
	ruff format .

shell:
	docker compose exec api bash
