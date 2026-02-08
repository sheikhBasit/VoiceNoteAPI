#!/bin/bash

# Run migrations with auto-recovery for squashed migrations
echo "Running database migrations..."

# Capture both stdout and stderr
alembic -c /app/alembic.ini upgrade head 2>&1 | tee /tmp/alembic_output.log

# Check if migration failed due to missing revision
if grep -q "Can't locate revision" /tmp/alembic_output.log; then
    echo "========================================="
    echo "Detected missing migration history (likely due to squash)."
    echo "Force-stamping database to latest head: b891cb8863b5"
    echo "========================================="
    
    alembic -c /app/alembic.ini stamp b891cb8863b5
    
    if [ $? -eq 0 ]; then
        echo "Stamp successful. Running upgrade..."
        alembic -c /app/alembic.ini upgrade head
        
        if [ $? -eq 0 ]; then
            echo "Migration recovery completed successfully!"
        else
            echo "ERROR: Migration upgrade failed after stamp. Exiting..."
            exit 1
        fi
    else
        echo "ERROR: Failed to stamp database. Exiting..."
        exit 1
    fi
elif grep -q "ERROR" /tmp/alembic_output.log; then
    echo "Migration encountered errors but will continue startup..."
fi

# Cleanup
rm -f /tmp/alembic_output.log

# Start application
echo "========================================="
echo "Starting FastAPI application..."
echo "========================================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
