#!/bin/bash

# VoiceNote Deployment Script
# Usage: ./scripts/deploy.sh [user@host]

SERVER=${1:-"root@4.240.96.60"}
REMOTE_DIR="/opt/voicenote-api"

echo "🚀 Deploying VoiceNote API to $SERVER..."

# 1. Sync Files (excluding large/unnecessary dirs)
echo "📦 Syncing files..."
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' --exclude 'uploads' \
    --exclude 'test.db' --exclude '.pytest_cache' \
    ./ $SERVER:$REMOTE_DIR

# 2. Remote Build & Restart
echo "🔄 Building and Restarting on Remote..."
ssh $SERVER << EOF
    cd $REMOTE_DIR
    
    # Ensure Docker is running
    # systemctl start docker
    
    # Use Makefile automation
    make build
    make down
    make up
    
    # cleanup unused images
    docker image prune -f
EOF

echo "✅ Deployment Complete!"
