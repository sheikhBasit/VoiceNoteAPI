#!/bin/bash

# VoiceNote Deployment Script
# Usage: ./scripts/deploy.sh

# Configuration
KEY_PATH="/home/basitdev/Downloads/voice_note_ai.pem"
SERVER_USER="azureuser"
SERVER_IP="4.240.96.60"
REMOTE_DIR="/home/azureuser/voicenote-project/VoiceNoteAPI"

# Ensure strict permissions on the key (required by SSH)
if [ -f "$KEY_PATH" ]; then
    chmod 400 "$KEY_PATH"
else
    echo "❌ SSH Key not found at $KEY_PATH"
    exit 1
fi

echo "🚀 Deploying VoiceNote API to $SERVER_USER@$SERVER_IP..."

# 1. Sync Files
# We use -e to pass the ssh command with the identity file
echo "📦 Syncing files..."
rsync -avz -e "ssh -i $KEY_PATH -o StrictHostKeyChecking=no" \
    --exclude 'venv' \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude 'uploads' \
    --exclude 'test.db' \
    --exclude '.pytest_cache' \
    --exclude '.idea' \
    ./ $SERVER_USER@$SERVER_IP:$REMOTE_DIR

# 2. Remote Build & Restart
echo "🔄 Building and Restarting on Remote..."
ssh -i "$KEY_PATH" -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP << EOF
    set -e
    cd $REMOTE_DIR
    
    echo "📂 Working directory: \$(pwd)"
    
    # Ensure Docker is available
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker not found on remote server"
        exit 1
    fi
    
    echo "🧹 Reclaiming disk space..."
    docker system prune -af
    docker volume prune -f
    
    # Force remove potential conflict containers
    docker rm -f voicenote_node_exporter voicenote_api voicenote_db voicenote_redis || true

    echo "🐳 Rebuilding containers..."
    make build
    
    echo "🛑 Restarting services..."
    make down
    make up

    # Targeted health check for core services
    echo "⏳ Waiting for core services (db, redis, api) to be healthy..."
    for i in {1..120}; do
      # Note: No 'sudo' inside here since typically azureuser has permissions or it's handled by shell
      DOCKER_STATUS=$(docker compose ps --format json)
      
      # Handle cases where json format might not be supported or empty
      if [ -z "$DOCKER_STATUS" ]; then
          DOCKER_STATUS=$(docker compose ps)
          DB_HEALTH=$(echo "$DOCKER_STATUS" | grep -c "db.*healthy")
          REDIS_HEALTH=$(echo "$DOCKER_STATUS" | grep -c "redis.*healthy")
          API_HEALTH=$(echo "$DOCKER_STATUS" | grep -c "api.*healthy")
      else
          DB_HEALTH=$(echo "$DOCKER_STATUS" | grep '"Service":"db"' | grep -c '"Health":"healthy"')
          REDIS_HEALTH=$(echo "$DOCKER_STATUS" | grep '"Service":"redis"' | grep -c '"Health":"healthy"')
          API_HEALTH=$(echo "$DOCKER_STATUS" | grep '"Service":"api"' | grep -c '"Health":"healthy"')
      fi
      
      echo "   Status ($i/120): DB=$DB_HEALTH, Redis=$REDIS_HEALTH, API=$API_HEALTH"
      
      if [ "$DB_HEALTH" -eq 1 ] && [ "$REDIS_HEALTH" -eq 1 ] && [ "$API_HEALTH" -eq 1 ]; then
        echo "✅ Core services are healthy!"
        break
      fi
      
      sleep 2
      if [ $i -eq 120 ]; then
        echo "❌ Timing out waiting for services to be healthy."
        docker compose ps
        exit 1
      fi
    done
EOF

echo "✅ Deployment Complete!"
