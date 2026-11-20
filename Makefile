.PHONY: install run test lint

install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

test:
	pytest --cov=app

lint:
	ruff check .
	mypy app
