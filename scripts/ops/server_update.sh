#!/bin/bash

# VoiceNote Server-Side Update Script
# Triggered by cicd_listener.py

PROJECT_DIR="/home/azureuser/voicenote-api"

echo "========================================"
echo "🚀 Deployment triggered at $(date)"
echo "========================================"

cd $PROJECT_DIR || exit 1

# 1. Pull latest code
echo "📥 Pulling latest changes from git..."
git fetch --all
git reset --hard origin/main
git pull origin main

# 2. Rebuild and Restart
echo "🔄 Rebuilding Docker containers..."
# Assuming we use the makefile
make build
make down
make up

# 3. Cleanup
docker image prune -f

echo "✅ Update complete at $(date)"
