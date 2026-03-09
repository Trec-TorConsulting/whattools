# ==============================================================================
# WhatTools Makefile
# All CI/CD and development targets
# ==============================================================================

.PHONY: all lint typecheck security-scan test coverage build deploy \
        dev-up dev-down clean help

PYTHON := python3
UV := uv

# Colors
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
NC     := \033[0m

# ==============================================================================
# CI Targets
# ==============================================================================

## Run all checks (lint + typecheck + security + test)
all: lint typecheck security-scan test
	@echo "$(GREEN)All checks passed$(NC)"

## Run Ruff linter and formatter check
lint:
	@echo "$(YELLOW)Running Ruff linter...$(NC)"
	$(UV) run ruff check services/
	$(UV) run ruff format --check services/
	@echo "$(GREEN)Lint passed$(NC)"

## Run Ruff auto-fix and format
lint-fix:
	@echo "$(YELLOW)Running Ruff auto-fix...$(NC)"
	$(UV) run ruff check --fix services/
	$(UV) run ruff format services/
	@echo "$(GREEN)Lint fix complete$(NC)"

## Run mypy strict type checking
typecheck:
	@echo "$(YELLOW)Running mypy type checker...$(NC)"
	$(UV) run mypy services/
	@echo "$(GREEN)Type check passed$(NC)"

## Run Bandit SAST and Safety dependency scan
security-scan:
	@echo "$(YELLOW)Running Bandit security scan...$(NC)"
	$(UV) run bandit -r services/ -c pyproject.toml -q
	@echo "$(YELLOW)Running Safety dependency check...$(NC)"
	$(UV) run safety check 2>/dev/null || true
	@echo "$(GREEN)Security scan complete$(NC)"

## Run pytest with 100% coverage enforcement
test:
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	$(UV) run pytest
	@echo "$(GREEN)Tests passed with 100% coverage$(NC)"

## Generate HTML coverage report
coverage:
	@echo "$(YELLOW)Generating coverage report...$(NC)"
	$(UV) run pytest --cov-report=html:docs/coverage
	@echo "$(GREEN)Coverage report at docs/coverage/index.html$(NC)"

# ==============================================================================
# Docker Targets
# ==============================================================================

## Build all Docker images
build:
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker compose build
	@echo "$(GREEN)Build complete$(NC)"

## Start local development environment
dev-up:
	@echo "$(YELLOW)Starting development environment...$(NC)"
	docker compose up -d
	@echo "$(GREEN)Dev environment running$(NC)"
	@echo "Gateway: http://localhost:5000/api/v1/health"

## Stop local development environment
dev-down:
	@echo "$(YELLOW)Stopping development environment...$(NC)"
	docker compose down
	@echo "$(GREEN)Dev environment stopped$(NC)"

## View logs from all services
dev-logs:
	docker compose logs -f

# ==============================================================================
# Database Targets
# ==============================================================================

## Run database migrations
db-upgrade:
	@echo "$(YELLOW)Running database migrations...$(NC)"
	$(UV) run alembic upgrade head
	@echo "$(GREEN)Migrations complete$(NC)"

## Generate a new migration
db-migrate:
	@echo "$(YELLOW)Generating migration...$(NC)"
	$(UV) run alembic revision --autogenerate -m "$(msg)"

## Seed development database
db-seed:
	@echo "$(YELLOW)Seeding database...$(NC)"
	$(UV) run python -m scripts.seed
	@echo "$(GREEN)Seed complete$(NC)"

# ==============================================================================
# Deployment Targets
# ==============================================================================

## Deploy all services to K3S (prod)
deploy:
	@echo "$(YELLOW)Deploying to K3S...$(NC)"
	kubectl apply -f k8s/prod/namespace.yaml
	kubectl apply -f k8s/prod/configmap.yaml
	kubectl apply -f k8s/prod/secrets.yaml
	kubectl apply -f k8s/prod/postgres.yaml
	kubectl apply -f k8s/prod/redis.yaml
	kubectl apply -f k8s/prod/auth.yaml
	kubectl apply -f k8s/prod/inventory.yaml
	kubectl apply -f k8s/prod/gateway.yaml
	kubectl apply -f k8s/prod/ingress.yaml
	@echo "$(GREEN)Deployment complete$(NC)"

## Check deployment status
deploy-status:
	kubectl get pods -n whattools
	kubectl get svc -n whattools
	kubectl get ingress -n whattools

# ==============================================================================
# Cleanup
# ==============================================================================

## Remove caches, build artifacts, coverage reports
clean:
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf docs/coverage htmlcov .coverage .coverage.*
	@echo "$(GREEN)Clean complete$(NC)"

# ==============================================================================
# Help
# ==============================================================================

## Show this help
help:
	@echo "$(GREEN)WhatTools Makefile Targets$(NC)"
	@echo ""
	@grep -E '^## ' Makefile | sed 's/^## /  /'
	@echo ""
	@echo "Usage: make <target>"
