# Variables
COMPOSE=docker-compose
API_SERVICE=api
WORKER_SERVICE=worker

.PHONY: help build up down restart logs test shell clean

help:
	@echo "VoiceNote AI Backend Commands:"
	@echo "  make build      - Build Docker containers"
	@echo "  make up         - Start all services (detached)"
	@echo "  make down       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View real-time logs"
	@echo "  make test       - Run local Pytest suite"
	@echo "  make clean      - Remove temp uploads and pycache"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) down && $(COMPOSE) up -d

logs:
	$(COMPOSE) logs -f

test:
	$(COMPOSE) run --rm $(API_SERVICE) pytest tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf uploads/*
	rm -f .pytest_cache