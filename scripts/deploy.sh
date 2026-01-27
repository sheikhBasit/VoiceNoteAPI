#!/bin/bash

# VoiceNote Deployment Script
# Usage: ./scripts/deploy.sh

# Configuration
KEY_PATH="/home/basitdev/Downloads/voice_note_ai.pem"
SERVER_USER="azureuser"
SERVER_IP="4.240.96.60"
REMOTE_DIR="/home/azureuser/voicenote-api"

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
    
    echo "🐳 Rebuilding containers..."
    make build
    
    echo "🛑 Restarting services..."
    make down
    make up
    
    echo "🧹 Cleaning up..."
    docker image prune -f
EOF

echo "✅ Deployment Complete!"
