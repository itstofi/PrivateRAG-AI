.PHONY: install setup migrate run-api run-ui test lint typecheck format clean docker-up docker-down check-ollama list-models sample-workspace load-samples evaluate

install:
	uv sync --extra dev

setup:
	cp -n .env.example .env || true
	uv run python -m scripts.init_db

migrate:
	uv run alembic upgrade head

run-api:
	uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

run-ui:
	uv run streamlit run frontend/streamlit_app.py

test:
	uv run pytest --cov=app --cov-report=term-missing

lint:
	uv run ruff format --check .
	uv run ruff check .

typecheck:
	uv run mypy app frontend scripts

format:
	uv run ruff format .
	uv run ruff check --fix .

clean:
	find . -type d -name __pycache__ -prune -exec rm -r {} +
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage build dist

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down

check-ollama:
	uv run python -m scripts.check_ollama

list-models:
	uv run python -m scripts.list_models

sample-workspace:
	uv run python -m scripts.create_sample_workspace

load-samples:
	uv run python -m scripts.load_samples

evaluate:
	uv run python -m scripts.evaluate_rag
