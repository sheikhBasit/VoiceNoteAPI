# 🐳 Docker Setup & Deployment Guide

## Quick Start

```bash
# 1. Build all containers
make build

# 2. Start all services
make up

# 3. Seed database
make seed

# 4. Check health
make health

# 5. View logs
make logs
```

---

## 📋 Complete Service Architecture

### Services Running in Docker

```
┌─────────────────────────────────────────────────────────────┐
│                  VoiceNote Full Stack                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐      ┌──────────────┐    ┌────────────┐  │
│  │   Nginx     │      │  FastAPI     │    │  Celery    │  │
│  │  Reverse    │─────▶│    API       │◀───│  Worker    │  │
│  │   Proxy     │      │  :8000       │    │  :8001     │  │
│  │   :80/443   │      └──────────────┘    └────────────┘  │
│  └─────────────┘            ▲                   ▲          │
│         ▲                   │                   │          │
│         │         ┌─────────▼────────────────────┐         │
│         │         │   PostgreSQL Database        │         │
│         │         │   with pgvector Extension    │         │
│         │         │   Port: 5432                 │         │
│         │         └─────────────────────────────┘         │
│         │                                                  │
│         └──────────────────────────┐                       │
│                                    │                       │
│                    ┌───────────────▼────────────┐          │
│                    │   PgAdmin (DB UI)          │          │
│                    │   Port: 5050               │          │
│                    └────────────────────────────┘          │
│                                                            │
│  ┌──────────────────────┐    ┌──────────────────────┐    │
│  │  Celery Beat         │    │   Redis              │    │
│  │  (Scheduler)         │───▶│   (Message Broker)   │    │
│  │  :8001               │    │   Port: 6379         │    │
│  └──────────────────────┘    └──────────────────────┘    │
│                                                            │
└─────────────────────────────────────────────────────────────┘
```

### Services Details

| Service | Image | Port | Purpose | Health Check |
|---------|-------|------|---------|--------------|
| **PostgreSQL** | `ankane/pgvector:latest` | 5432 | Main database with vector support | `pg_isready` |
| **Redis** | `redis:7-alpine` | 6379 | Message broker & caching | `redis-cli ping` |
| **FastAPI** | Custom build | 8000 | REST API server | HTTP `/health` |
| **Celery Worker** | Custom build | N/A | Background task processing | Log monitoring |
| **Celery Beat** | Custom build | N/A | Task scheduling | Log monitoring |
| **PgAdmin** | `dpage/pgadmin4:latest` | 5050 | PostgreSQL UI client | HTTP `/misc/ping` |
| **Nginx** | `nginx:alpine` | 80/443 | Reverse proxy & SSL termination | HTTP GET / |

---

## 🗄️ Database & Seeding

### Seeding Methods

#### 1. **SQL Seeding (Automatic on Startup)**
```bash
# Runs automatically from scripts/init.sql and scripts/seed.sql
# Enables pgvector extension
# Creates admin, moderator, and viewer users
# Creates sample test users

# Or run manually:
make seed-sql
```

**Location:** `scripts/seed.sql`

**What it seeds:**
- ✅ Admin user with full permissions
- ✅ Moderator user with moderation permissions
- ✅ Viewer user with read-only analytics permissions
- ✅ 3 test users for development

#### 2. **Python ORM Seeding**
```bash
# Run from inside container
make seed-python

# Or manually
python scripts/seed_db.py
```

**Location:** `scripts/seed_db.py`

**What it seeds:**
- ✅ Admin users (full permissions)
- ✅ Moderator users (content moderation)
- ✅ Viewer users (analytics only)
- ✅ 10 test users
- ✅ Sample notes per user
- ✅ Sample tasks per note

#### 3. **Complete Seeding (Both Methods)**
```bash
# SQL + Python seeding
make seed

# Or manually
docker-compose exec -T db psql -U postgres -d voicenote -f /docker-entrypoint-initdb.d/02-seed.sql
docker-compose run --rm api python scripts/seed_db.py
```

### Database Commands

```bash
# Access PostgreSQL shell
make db-shell

# Backup database
make db-backup

# Reset database completely (⚠️ WARNING: Deletes all data!)
make db-reset

# View database logs
make logs-db
```

---

## 🚀 Makefile Commands Reference

### Build & Deployment

```bash
make build              # Build all containers
make build-no-cache    # Build without cache
make up                # Start all services
make down              # Stop all services
make restart           # Restart all services
make status            # Show service status
```

### Database

```bash
make seed              # SQL + Python seeding
make seed-sql          # SQL seeding only
make seed-python       # Python ORM seeding
make db-shell          # PostgreSQL shell
make db-reset          # Reset database
make db-backup         # Backup database
```

### Logs & Debugging

```bash
make logs              # All service logs
make logs-api          # API logs only
make logs-worker       # Celery worker logs
make logs-beat         # Celery beat logs
make logs-db           # Database logs
```

### Testing

```bash
make test              # Run all tests
make test-admin        # Admin system tests
make test-coverage     # Tests with coverage
```

### Maintenance

```bash
make health            # Health check all services
make clean             # Clean temporary files
make shell             # API container shell
make shell-worker      # Worker container shell
make fresh-start       # Full setup from scratch
make dev               # Development mode
```

---

## 📊 Health Checks

All services have health checks:

### PostgreSQL
```bash
# Command inside container
pg_isready -U postgres -d voicenote

# Via Makefile
make health
```

### Redis
```bash
# Command inside container
redis-cli ping

# Via Makefile
make health
```

### FastAPI
```bash
# HTTP endpoint
GET http://localhost:8000/health

# Via Makefile
make health
```

### PgAdmin
```bash
# HTTP endpoint
GET http://localhost:5050/misc/ping

# Via Makefile
make health
```

---

## 🔒 SSL/TLS Setup

### Generate Self-Signed Certificates (Development)

```bash
mkdir -p certs
cd certs

# Generate private key
openssl genrsa -out key.pem 2048

# Generate certificate
openssl req -new -x509 -key key.pem -out cert.pem -days 365

cd ..
```

### Update nginx.conf for Production

```bash
# Replace certificate paths in nginx.conf
ssl_certificate /path/to/cert.pem;
ssl_certificate_key /path/to/key.pem;
```

---

## 📝 Volumes & Data Persistence

```yaml
volumes:
  postgres_data:       # PostgreSQL data directory
  redis_data:          # Redis data persistence
  pgadmin_data:        # PgAdmin configuration
  uploads:             # Application uploads
  logs:                # Application logs
```

### Backup Volumes
```bash
# Backup all volumes
docker-compose exec db pg_dump -U postgres voicenote > backup.sql

# Restore
docker-compose exec -T db psql -U postgres voicenote < backup.sql
```

---

## 🌐 Network Configuration

### Network Details
```
Network: voicenote_network (bridge)
- All services connected
- Service discovery via DNS (service name as hostname)
- Database: db:5432
- Redis: redis:6379
- API: api:8000
```

### Environment Variables

**Inside containers:**
```
DATABASE_URL: postgresql+asyncpg://postgres:password@db:5432/voicenote
REDIS_URL: redis://redis:6379/0
CELERY_BROKER_URL: redis://redis:6379/0
CELERY_RESULT_BACKEND: redis://redis:6379/1
```

---

## 📊 Logging

### Log Drivers
All services configured with:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"  # Keep 3 rotated files
```

### View Logs
```bash
# All services
make logs

# Specific service
make logs-api
make logs-worker
make logs-db

# Raw Docker command
docker-compose logs -f [service_name]

# Last 100 lines
docker-compose logs -f --tail=100 [service_name]
```

---

## 🔧 VS Code Launch Configuration

### Available Configurations

1. **Python: FastAPI (Local)** - Run API locally
2. **Python: Seed Database** - Run seeding script
3. **Python: Run Tests** - Run admin system tests
4. **Python: Run All Tests** - Run all tests
5. **Python: Celery Worker** - Run background worker
6. **Python: Celery Beat** - Run task scheduler

### Compound Configurations

- **Full Stack (API + Worker)** - Run both
- **Full Stack (API + Worker + Beat)** - Run all three

---

## ⚙️ Performance Tuning

### PostgreSQL Settings

In docker-compose.yml:
```
max_connections=200
shared_buffers=256MB
```

### Connection Pooling

```
Pool size: 10
Overflow: 10
Pre-ping: enabled
```

### Redis Configuration

```bash
# Persistence enabled
redis-server --appendonly yes

# Memory policy
maxmemory-policy allkeys-lru
```

---

## 🚨 Troubleshooting

### Service Won't Start

```bash
# Check logs
make logs

# Check health
make health

# Verify containers
docker-compose ps

# Restart everything
make restart
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
make db-shell

# Check database status
docker-compose exec db pg_isready -U postgres

# View database logs
make logs-db
```

### Redis Issues

```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Clear Redis cache
docker-compose exec redis redis-cli FLUSHALL

# View Redis logs
make logs
```

### API Health Issues

```bash
# Test API endpoint
curl http://localhost:8000/health

# View API logs
make logs-api

# Restart API only
docker-compose restart api
```

---

## 📦 Environment Variables

Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/voicenote
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=voicenote

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Application
ENVIRONMENT=production
PYTHONUNBUFFERED=1
```

---

## 🎯 Complete Workflow Example

```bash
# 1. Initial setup
make fresh-start

# 2. Check everything is running
make health

# 3. View logs
make logs

# 4. Access database
make db-shell

# 5. Run tests
make test

# 6. Backup database
make db-backup

# 7. Continue development...
make logs-api

# 8. Stop when done
make down
```

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.io/)

---

**Happy Deploying! 🎉**
