.PHONY: help up down test check math report

help:
	@echo "DOGFOOD 2026 - Available Commands:"
	@echo "  make up       - Build and launch portal via Docker Compose (port 8080)"
	@echo "  make down     - Stop portal containers"
	@echo "  make check    - Run official acceptance harness (run.py .dogfood.toml)"
	@echo "  make test     - Run pytest integration test suite (15 tests)"
	@echo "  make math     - Run mathematical normalization audit in terminal"
	@echo "  make report   - Generate fresh acceptance-report.txt"

up:
	docker compose up --build

down:
	docker compose down

check:
	python run.py .dogfood.toml

test:
	python -m pytest tests/test_platform.py -v

math:
	python src/normalization.py

report:
	python run.py .dogfood.toml > acceptance-report.txt
