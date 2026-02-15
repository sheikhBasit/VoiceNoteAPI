#!/bin/bash
# Diagnostic script to check DB health on the server

echo "=== Container Status ==="
sudo docker compose ps

echo ""
echo "=== DB Container Health ==="
sudo docker inspect voicenote_db --format='{{json .State.Health}}' | jq '.'

echo ""
echo "=== DB Container Logs (last 100 lines) ==="
sudo docker compose logs db --tail=100

echo ""
echo "=== Disk Space ==="
df -h

echo ""
echo "=== Docker Volume List ==="
sudo docker volume ls
