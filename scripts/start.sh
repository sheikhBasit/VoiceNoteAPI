#!/bin/bash
set -e

# Run migrations
echo "Running database migrations..."
# Attempt upgrade, if it fails because of the squashed migration history, force-stamp the DB
if ! alembic -c /app/alembic.ini upgrade head 2>/tmp/alembic_err; then
    error_msg=$(cat /tmp/alembic_err)
    echo "$error_msg"
    if [[ "$error_msg" == *"Can't locate revision"* ]]; then
        echo "Detected missing migration history (likely due to squash). Force-stamping to latest head..."
        alembic -c /app/alembic.ini stamp b891cb8863b5
        alembic -c /app/alembic.ini upgrade head
    else
        echo "Migration failed for other reasons. Continuing anyway..."
    fi
fi
rm -f /tmp/alembic_err

# Start application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
