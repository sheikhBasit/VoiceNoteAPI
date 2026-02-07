# VoiceNote API - Commands and Services Check

This document provides a reference for running the VoiceNote API, executing tests, and verifying the health of all integrated services.

## 1. Running the Application

The application is containerized using Docker.

### Start All Services
```bash
docker-compose up -d --build
```

### View Logs
```bash
docker-compose logs -f
```
To view logs for a specific service:
```bash
docker-compose logs -f api
docker-compose logs -f worker
```

### Stop All Services
```bash
docker-compose down
```

## 2. Running Tests

Tests are written using `pytest`.

### Run All Tests
```bash
# Run inside the local environment (requires dependencies installed)
PYTHONPATH=. pytest

# Run inside the Docker container
docker-compose exec api pytest
```

### Run Specific Test File
```bash
PYTHONPATH=. pytest tests/test_restoration_endpoints.py
```

## 3. Checking Services Status

You can verify the status of individual services using Docker commands.

### PostgreSQL (Database)
Check if the database is accepting connections:
```bash
docker-compose exec postgres pg_isready -U postgres
```
Connect to the database CLI:
```bash
docker-compose exec postgres psql -U postgres -d voicenote
```

### Redis (Cache & Broker)
Ping the Redis server:
```bash
docker-compose exec redis redis-cli ping
# Expected Output: PONG
```

### Celery (Worker)
Check worker status (assuming Celery is running as 'worker' service):
```bash
# Check running processes in the container
docker-compose exec worker celery -A app.worker.celery_app status
```

### MinIO (Object Storage)
Check if MinIO is responding (via curl inside a container or from host if port mapped):
```bash
curl -I http://localhost:9000/minio/health/live
```

### Prometheus (Metrics)
Check health endpoint:
```bash
curl -I http://localhost:9090/-/healthy
```

### API Health Check
Check the main API health endpoint:
```bash
curl http://localhost:8000/health
# Expected Output: {"status": "ok"}
```

## 4. Useful Maintenance Commands

### Reset Database (Caution: Deletes all data)
```bash
docker-compose down -v
docker-compose up -d
```

### Run Database Migrations (Alembic)
```bash
docker-compose exec api alembic upgrade head
```
