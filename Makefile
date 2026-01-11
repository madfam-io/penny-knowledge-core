# =============================================================================
# PENNY Knowledge Core - Makefile
# =============================================================================

.PHONY: help install dev test lint format type-check clean docker-up docker-down docker-build ui ui-dev

# Default target
help:
	@echo "PENNY Knowledge Core - Development Commands"
	@echo ""
	@echo "Installation:"
	@echo "  make install     Install production dependencies"
	@echo "  make dev         Install development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make test        Run tests"
	@echo "  make lint        Run linter (ruff)"
	@echo "  make format      Format code (ruff)"
	@echo "  make type-check  Run type checker (mypy)"
	@echo "  make check       Run all checks (lint, type-check, test)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build    Build Docker images"
	@echo "  make docker-up       Start the Hydra fleet"
	@echo "  make docker-down     Stop the Hydra fleet"
	@echo "  make docker-logs     View container logs"
	@echo ""
	@echo "UI (Phase 4):"
	@echo "  make ui          Run Chainlit UI (production)"
	@echo "  make ui-dev      Run Chainlit UI with hot reload"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       Remove build artifacts and caches"

# =============================================================================
# Installation
# =============================================================================

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

# =============================================================================
# Development
# =============================================================================

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src/penny_knowledge_core --cov-report=html

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/

check: lint type-check test

# =============================================================================
# Docker
# =============================================================================

docker-build:
	docker compose -f docker/docker-compose.yml build

docker-up:
	docker compose -f docker/docker-compose.yml up -d

docker-up-full:
	docker compose -f docker/docker-compose.yml --profile full up -d

docker-down:
	docker compose -f docker/docker-compose.yml down

docker-logs:
	docker compose -f docker/docker-compose.yml logs -f

docker-dev:
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

# =============================================================================
# Running
# =============================================================================

run:
	python -m penny_knowledge_core.server.main

run-dev:
	RELOAD=true DEBUG=true python -m uvicorn penny_knowledge_core.server.main:app --host 0.0.0.0 --port 8000 --reload

# =============================================================================
# UI (Phase 4 - Chainlit)
# =============================================================================

ui:
	python -m chainlit run src/penny_knowledge_core/ui/app.py --host 0.0.0.0 --port 8080

ui-dev:
	DEBUG=true python -m chainlit run src/penny_knowledge_core/ui/app.py --host 0.0.0.0 --port 8080 --watch

# =============================================================================
# Cleanup
# =============================================================================

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
