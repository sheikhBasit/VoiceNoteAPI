#!/bin/bash
set -e

# Run migrations
echo "Running database migrations..."
alembic -c /app/alembic.ini upgrade head || echo "Migration skipped or failed, continuing..."

# Start application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
