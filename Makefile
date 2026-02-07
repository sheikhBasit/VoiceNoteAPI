# VoiceNote Docker Compose Commands & Development Tools
# Variables
COMPOSE=docker compose
API_SERVICE=api
WORKER_SERVICE=celery_worker
BEAT_SERVICE=celery_beat

.PHONY: help build up down restart logs test clean seed seed-sql seed-python db-shell db-reset health status run dev format lint test-quick test-fast install-hooks

help:
	@echo "========================================="
	@echo "VoiceNote AI Backend - Development CLI"
	@echo "========================================="
	@echo ""
	@echo "🚀 QUICK START:"
	@echo "  make dev                - Start development environment"
	@echo "  make install-hooks      - Setup git hooks for CI/CD"
	@echo ""
	@echo "🏗️  BUILD & DEPLOYMENT:"
	@echo "  make build              - Build all Docker containers"
	@echo "  make build-no-cache     - Build without cache"
	@echo "  make up                 - Start all services"
	@echo "  make down               - Stop all services"
	@echo "  make restart            - Restart all services"
	@echo "  make status             - Show service status"
	@echo ""
	@echo "📊 LOGS & DEBUGGING:"
	@echo "  make logs               - View all logs"
	@echo "  make logs-api           - View API logs only"
	@echo "  make logs-worker        - View Celery Worker logs"
	@echo "  make logs-beat          - View Celery Beat logs"
	@echo "  make logs-db            - View Database logs"
	@echo ""
	@echo "🗄️  DATABASE MANAGEMENT:"
	@echo "  make seed               - Seed database (SQL + Python)"
	@echo "  make seed-sql           - Seed via SQL scripts"
	@echo "  make seed-python        - Seed via Python ORM"
	@echo "  make db-shell           - Open PostgreSQL shell"
	@echo "  make db-reset           - Reset database completely"
	@echo "  make db-backup          - Backup database"
	@echo ""
	@echo "🧪 TESTING:"
	@echo "  make test               - Run all tests"
	@echo "  make test-quick         - Run fast tests only (unit + quick integration)"
	@echo "  make test-fast          - Run failed tests first"
	@echo "  make test-admin         - Run admin system tests"
	@echo "  make test-coverage      - Run tests with coverage report"
	@echo "  make test-watch         - Run tests in watch mode"
	@echo ""
	@echo "✨ CODE QUALITY:"
	@echo "  make format             - Auto-format code (Black + isort)"
	@echo "  make lint               - Run code quality checks"
	@echo "  make lint-fix           - Auto-fix linting issues"
	@echo "  make security-check     - Run security scan"
	@echo ""
	@echo "⚙️  DEVELOPMENT:"
	@echo "  make shell              - Open API container shell"
	@echo "  make shell-worker       - Open Celery worker shell"
	@echo "  make fresh-start        - Fresh start (clean, build, seed)"
	@echo "  make run                - Run API locally (without containers)"
	@echo "  make health             - Health check all services"
	@echo ""
	@echo "📦 UTILITIES:"
	@echo "  make clean              - Clean temporary files"
	@echo "  make install-hooks      - Install pre-push git hooks"
	@echo ""
	@echo "========================================="

# Build
build:
	$(COMPOSE) build

build-no-cache:
	$(COMPOSE) build --no-cache

# Startup & Shutdown
up:
	@echo "🚀 Starting all services..."
	$(COMPOSE) up -d
	@sleep 5
	@echo "✅ Services started!"
	@make health

down:
	@echo "🛑 Stopping all services..."
	$(COMPOSE) down
	@echo "✅ Services stopped!"

restart:
	@echo "🔄 Restarting all services..."
	$(COMPOSE) down && $(COMPOSE) up -d
	@sleep 5
	@echo "✅ Services restarted!"
	@make health

# Logs
logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f $(API_SERVICE)

logs-worker:
	$(COMPOSE) logs -f $(WORKER_SERVICE)

logs-beat:
	$(COMPOSE) logs -f $(BEAT_SERVICE)

logs-db:
	$(COMPOSE) logs -f db

# Database Management
seed: seed-sql seed-python
	@echo "✅ Database fully seeded!"

seed-sql:
	@echo "🌱 Seeding database via SQL..."
	@docker-compose exec -T db psql -U postgres -d voicenote -f /docker-entrypoint-initdb.d/02-seed.sql
	@echo "✅ SQL seeding complete!"

seed-python:
	@echo "🌱 Seeding database via Python..."
	@$(COMPOSE) run --rm $(API_SERVICE) python scripts/seed_db.py
	@echo "✅ Python seeding complete!"

db-shell:
	@echo "🔗 Opening PostgreSQL shell..."
	$(COMPOSE) exec db psql -U postgres -d voicenote

db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		$(COMPOSE) exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS voicenote;"; \
		$(COMPOSE) exec -T db psql -U postgres -c "CREATE DATABASE voicenote;"; \
		make seed; \
		echo "✅ Database reset and reseeded!"; \
	else \
		echo "❌ Cancelled."; \
	fi

db-backup:
	@echo "📦 Backing up database..."
	@mkdir -p backups
	@docker-compose exec -T db pg_dump -U postgres voicenote > backups/voicenote_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup created!"

# Testing
test:
	@echo "🧪 Running all tests..."
	$(COMPOSE) run --rm -T -e PYTHONPATH=/app $(API_SERVICE) python -m pytest tests/ -v

test-quick:
	@echo "⚡ Running quick tests (unit + fast integration)..."
	$(COMPOSE) run --rm -T -e PYTHONPATH=/app $(API_SERVICE) python -m pytest tests/test_core.py tests/test_main.py tests/test_new_endpoints.py -v -m "not load and not stress and not performance"

test-fast:
	@echo "⚡ Running failed tests first..."
	$(COMPOSE) run --rm -T -e PYTHONPATH=/app $(API_SERVICE) python -m pytest tests/ --last-failed --maxfail=1 -v

test-admin:
	@echo "🧪 Running admin system tests..."
	$(COMPOSE) run --rm -T -e PYTHONPATH=/app $(API_SERVICE) python -m pytest tests/test_admin_system.py -v

test-coverage:
	@echo "🧪 Running tests with coverage..."
	$(COMPOSE) run --rm -T -e PYTHONPATH=/app $(API_SERVICE) python -m pytest tests/ --cov=app --cov-report=html --cov-report=term

test-watch:
	@echo "👀 Running tests in watch mode..."
	$(COMPOSE) run --rm -T -e PYTHONPATH=/app $(API_SERVICE) python -m pytest-watch tests/ -- -v

# Code Quality & Formatting
format:
	@echo "📝 Formatting code with Black and isort..."
	$(COMPOSE) run --rm -T $(API_SERVICE) python -m black app/ tests/
	$(COMPOSE) run --rm -T $(API_SERVICE) python -m isort app/ tests/
	@echo "✅ Code formatted!"

lint:
	@echo "🔍 Running linting checks..."
	$(COMPOSE) run --rm -T $(API_SERVICE) python -m flake8 app/ tests/ --count --max-complexity=10 --max-line-length=127
	$(COMPOSE) run --rm -T $(API_SERVICE) python -m pylint app/ --exit-zero --disable=all --enable=C,E,F,W
	@echo "✅ Lint check complete!"

lint-fix:
	@echo "🔧 Auto-fixing linting issues..."
	$(COMPOSE) run --rm -T $(API_SERVICE) python -m black app/ tests/
	$(COMPOSE) run --rm -T $(API_SERVICE) python -m isort app/ tests/
	@echo "✅ Linting issues fixed!"

security-check:
	@echo "🔐 Running security scan..."
	$(COMPOSE) run --rm -T $(API_SERVICE) bandit -r app/ -ll -ii
	@echo "✅ Security check complete!"

# Health Check
health:
	@echo "🏥 Checking service health..."
	@echo ""
	@echo "Database (PostgreSQL):"
	@docker-compose exec -T db pg_isready -U postgres || echo "❌ Database not ready"
	@echo ""
	@echo "Redis:"
	@docker-compose exec -T redis redis-cli ping || echo "❌ Redis not ready"
	@echo ""
	@echo "API:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ API not ready"
	@echo ""
	@echo "PgAdmin:"
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5050 || echo "❌ PgAdmin not ready"

status:
	@echo "📊 Service Status:"
	@$(COMPOSE) ps

# Cleanup
clean:
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf uploads/* 2>/dev/null || true
	@rm -f .pytest_cache 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Shell access
shell:
	$(COMPOSE) exec $(API_SERVICE) /bin/bash

shell-worker:
	$(COMPOSE) exec $(WORKER_SERVICE) /bin/bash

# Full setup from scratch
fresh-start: clean build up seed
	@echo "✨ Fresh start complete!"
	@make health

# Development mode (useful for hot reload)
dev: up seed
	@echo "👨‍💻 Development environment ready!"
	@echo ""
	@echo "Available commands:"
	@echo "  make logs       - View logs"
	@echo "  make test-quick - Run fast tests"
	@echo "  make format     - Format code"
	@echo "  make lint       - Check code quality"
	@echo ""
	@make health

run:
	@echo "🚀 Starting infrastructure..."
	@docker compose up -d db redis
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo "📡 Starting FastAPI server..."
	@.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Git Hooks & Pre-push checks
install-hooks:
	@echo "📝 Installing git hooks..."
	@if [ -f scripts/pre-push-check.sh ]; then \
		chmod +x scripts/pre-push-check.sh; \
		cp scripts/pre-push-check.sh .git/hooks/pre-push; \
		chmod +x .git/hooks/pre-push; \
		echo "✅ Pre-push hook installed!"; \
	else \
		echo "❌ pre-push-check.sh not found!"; \
	fi
