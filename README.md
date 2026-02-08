# VoiceNote AI Backend

Professional-grade, intelligent voice-taking and task-management API.

## 📂 Project Structure

- `app/`: Core FastAPI application logic
  - `api/`: API endpoints (v1)
  - `core/`: Configuration and security
  - `db/`: Database models and session management
  - `services/`: Business logic and AI integrations
  - `worker/`: Celery task definitions
- `scripts/`: Organized utility scripts
  - `admin/`: Admin setup and moderation
  - `ai/`: Embedding generation and audio processing
  - `benchmark/`: Performance testing and evaluation
  - `db/`: Database initialization and seeding
  - `ops/`: Deployment and CI/CD operations
  - `test/`: Functional and integration test runners
  - `utils/`: Maintenance utilities
- `tests/`: Pytest suite (Unit, Integration, and Load tests)
- `docs/`: Comprehensive documentation
  - `api/`: Architecture and endpoint deep-dives
  - `admin/`: Admin system and roles
  - `ci-cd/`: Deployment and strategy
  - `testing/`: Test guides and reports
  - `archive/`: Historical summaries and status reports
- `backups/`: Database backups
- `logs/`: Application and system logs

## 🚀 Quick Start

1. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Update your API keys in .env
   ```

2. **Run with Docker**:
   ```bash
   make dev
   ```

3. **Run Tests**:
   ```bash
   make test
   ```

## 🛠️ Development Tools

Use the `Makefile` for common tasks:
- `make seed`: Populate the database with sample data
- `make db-reset`: Reset and reseed the database
- `make format`: Auto-format code with Black and isort
- `make lint`: Run code quality checks
- `make help`: See all available commands
