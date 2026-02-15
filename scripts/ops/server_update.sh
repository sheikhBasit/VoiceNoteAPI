#!/bin/bash

# VoiceNote Server-Side Update Script
# Triggered by cicd_listener.py

PROJECT_DIR="/home/azureuser/voicenote-project/VoiceNoteAPI"

echo "========================================"
echo "🚀 Deployment started at $(date)"
echo "========================================"

# Login to Docker Hub to fix rate limit (Assumes variables are set in ENV)
if [ ! -z "$DOCKER_PASSWORD" ] && [ ! -z "$DOCKER_USERNAME" ]; then
    echo "🔑 Logging into Docker Hub..."
    echo "$DOCKER_PASSWORD" | sudo docker login -u "$DOCKER_USERNAME" --password-stdin
fi

cd $PROJECT_DIR || exit 1

# 1. Pull latest code
echo "📥 Pulling latest changes from git..."
git fetch --all
git reset --hard origin/main
git pull origin main

# 2. Reset and Prune
echo "🧹 Cleaning up existing state and volumes..."
sudo docker compose down -v
sudo docker system prune -af
sudo docker volume prune -f

# Force remove potentially conflicting containers (Fix for name conflict)
echo "🛑 Removing potential conflict containers..."
sudo docker rm -f voicenote_node_exporter voicenote_api voicenote_db voicenote_redis || true

# 3. Pull and Start
echo "🐳 Pulling latest images..."
sudo docker compose pull

echo "📦 Starting all services with fresh state..."
sudo docker compose up -d --no-build

# 4. Targeted health check for core services
echo "⏳ Waiting for core services (db, redis, api) to be healthy..."
for i in {1..120}; do
  DOCKER_STATUS=$(sudo docker compose ps --format json)
  DB_HEALTH=$(echo "$DOCKER_STATUS" | grep '"Service":"db"' | grep -c '"Health":"healthy"')
  REDIS_HEALTH=$(echo "$DOCKER_STATUS" | grep '"Service":"redis"' | grep -c '"Health":"healthy"')
  API_HEALTH=$(echo "$DOCKER_STATUS" | grep '"Service":"api"' | grep -c '"Health":"healthy"')
  
  echo "   Status ($i/120): DB=$DB_HEALTH, Redis=$REDIS_HEALTH, API=$API_HEALTH"
  
  if [ "$DB_HEALTH" -eq 1 ] && [ "$REDIS_HEALTH" -eq 1 ] && [ "$API_HEALTH" -eq 1 ]; then
    echo "✅ Core services are healthy!"
    break
  fi
  
  # If DB and Redis are healthy but API is not even running, try to force start it
  if [ "$DB_HEALTH" -eq 1 ] && [ "$REDIS_HEALTH" -eq 1 ]; then
    API_RUNNING=$(echo "$DOCKER_STATUS" | grep '"Service":"api"' | grep -c '"State":"running"')
    if [ "$API_RUNNING" -eq 0 ]; then
      echo "⚠️ API service not running but dependencies are healthy. Force starting API..."
      sudo docker compose up -d api
    fi
  fi
  
  sleep 2
  
  if [ $i -eq 120 ]; then
    echo "❌ Timing out waiting for services to be healthy."
    sudo docker compose ps
    sudo docker compose logs db
    sudo docker compose logs api
    exit 1
  fi
done

echo "========================================"
echo "✅ Deployment complete at $(date)"
echo "========================================"
