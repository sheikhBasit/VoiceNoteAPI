---
description: How to deploy the VoiceNote API using Docker Compose
---
// turbo-all
# Deployment Workflow

Follow these steps to deploy the application in a production-ready environment.

### 1. Prerequisites
Ensure you have the following installed:
- Docker (20.10+)
- Docker Compose (1.29+)
- Make (optional, but recommended)

### 2. Environment Configuration
Copy the example environment file and update the credentials:
```bash
cp .env.example .env
# Edit .env with your production credentials
```

### 3. Automated Setup (Recommended)
You can use the provided setup script to initialize the environment:
```bash
chmod +x automate_setup.sh
./automate_setup.sh
```

### 4. Manual Deployment
If you prefer manual steps, run the following:

#### Build and Start Services
```bash
docker-compose up --build -d
```

#### Run Database Migrations (if applicable)
```bash
docker-compose exec api scripts/run_migrations.sh
```

#### Seed Database (Initial Setup only)
```bash
docker-compose exec -T db psql -U postgres -d voicenote < scripts/seed.sql
```

### 5. Verification
Check if the services are healthy:
```bash
docker-compose ps
# curl http://localhost:80/health
```

### 6. Logs Monitoring
View logs for all services or specific ones:
```bash
docker-compose logs -f
# docker-compose logs -f api
```

### 7. Stopping the Application
```bash
docker-compose down
```
