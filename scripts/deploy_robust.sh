#!/bin/bash
set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

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
echo "🧹 Cleaning up old containers..."
# Use compose down to be safe, avoid aggressive system prune unless requested
docker compose down -v --remove-orphans

# 4. Pull latest images
echo "📥 Pulling latest images from registry..."
docker compose pull

# 5. Start Services
echo "🎬 Starting services..."
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
