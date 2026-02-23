#!/bin/bash
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Source .env so docker-compose can interpolate required variables
# (needed when running under sudo where auto .env loading is skipped)
if [ -f ".env" ]; then
    echo "📋 Loading environment from .env..."
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
else
    echo "⚠️  Warning: .env file not found at $PROJECT_DIR/.env"
fi

echo "🚀 Starting Robust Deployment for VoiceNoteAPI..."

# 1. Login to Docker Hub (if credentials provided)
if [ -n "$DOCKER_USERNAME" ] && [ -n "$DOCKER_PASSWORD" ]; then
    echo "Logging into Docker Hub..."
    echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
fi

# 2. Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# 3. Shutdown and Clean
echo "Sweep for accidental directories..."
[ -d scripts/init.sql ] && echo "Removing accidental directory scripts/init.sql" && rm -rf scripts/init.sql
[ -d scripts/seed.sql ] && echo "Removing accidental directory scripts/seed.sql" && rm -rf scripts/seed.sql

echo "🧹 Cleaning up old containers..."
docker compose down -v --remove-orphans

echo "♻️ Pruning unused docker images and resources to free up space..."
docker system prune -af

# 4. Pull latest images
echo "📥 Pulling latest images from registry..."
docker compose pull

# 5. Start Core Services First (Staged Startup)
echo "🎬 Starting core services (db, redis)..."
docker compose up -d db redis

echo "⏳ Waiting for core services to stabilize..."
for i in {1..30}; do
    DB_STATUS=$(docker inspect --format='{{.State.Health.Status}}' voicenote_db 2>/dev/null || echo "not-found")
    REDIS_STATUS=$(docker inspect --format='{{.State.Health.Status}}' voicenote_redis 2>/dev/null || echo "not-found")
    
    if [[ "$DB_STATUS" == "healthy" && "$REDIS_STATUS" == "healthy" ]]; then
        echo "✅ Core services are ready!"
        break
    fi
    echo "   [$i/30] DB: $DB_STATUS | Redis: $REDIS_STATUS"
    sleep 2
done

if [[ "$(docker inspect --format='{{.State.Health.Status}}' voicenote_db 2>/dev/null)" != "healthy" ]]; then
    echo "❌ Database failed to become healthy. Dumping DB logs..."
    docker compose logs db
    exit 1
fi

# 6. Start Remaining Services
echo "🎬 Starting remaining services..."
docker compose up -d

# 6. Advanced Health Check Loop
echo "⏳ Waiting for services to become healthy..."
MAX_ATTEMPTS=60
SLEEP_INTERVAL=5

for ((i=1; i<=MAX_ATTEMPTS; i++)); do
    DB_STATUS=$(docker inspect --format='{{.State.Health.Status}}' voicenote_db 2>/dev/null || echo "not-found")
    REDIS_STATUS=$(docker inspect --format='{{.State.Health.Status}}' voicenote_redis 2>/dev/null || echo "not-found")
    API_STATUS=$(docker inspect --format='{{.State.Health.Status}}' voicenote_api 2>/dev/null || echo "not-found")
    API_STATE=$(docker inspect --format='{{.State.Status}}' voicenote_api 2>/dev/null || echo "not-found")

    echo "   [$i/$MAX_ATTEMPTS] DB: $DB_STATUS | Redis: $REDIS_STATUS | API: $API_STATUS ($API_STATE)"

    if [[ "$DB_STATUS" == "healthy" && "$REDIS_STATUS" == "healthy" && "$API_STATUS" == "healthy" ]]; then
        echo "✅ All core services are healthy!"
        HEALTHY=true
        break
    fi

    # Detect if API is failing early
    if [[ "$API_STATE" == "exited" || "$API_STATE" == "restarting" ]]; then
        echo "⚠️ API container is in state: $API_STATE. Dumping logs..."
        docker compose logs api --tail=50
    fi

    sleep $SLEEP_INTERVAL
done

if [ "$HEALTHY" != "true" ]; then
    echo "❌ Timeout waiting for services to be healthy."
    echo "Dumping container statuses and logs for debugging..."
    docker compose ps
    docker compose logs --tail=100
    exit 1
fi

# 7. Run Migrations
echo "🔄 Running database migrations..."
if ! docker compose exec -T api alembic -c /app/alembic.ini upgrade head; then
    echo "❌ Migration failed! Dumping API logs..."
    docker compose logs api --tail=100
    exit 1
fi

# 8. Verify Final State
echo "✅ Deployment successful!"
docker compose ps
echo "Running smoke tests..."
if ! ./scripts/test/test_api.sh | head -n 50; then
    echo "⚠️ Smoke tests encountered some failures. Check logs."
fi

echo "✨ Done!"
