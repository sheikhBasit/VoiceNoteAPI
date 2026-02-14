#!/bin/bash

# Clean up any Python bytecode cache to prevent migration issues
echo "Cleaning Python cache..."
find /app/alembic -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find /app/alembic -type f -name "*.pyc" -delete 2>/dev/null || true
echo "Cache cleaned."

# Run migrations with auto-recovery for squashed migrations
echo "Running database migrations..."

# Capture both stdout and stderr
alembic -c /app/alembic.ini upgrade head 2>&1 | tee /tmp/alembic_output.log

# Check if migration failed due to missing revision
if grep -q "Can't locate revision" /tmp/alembic_output.log; then
    echo "========================================="
    echo "Detected missing migration history (likely due to squash)."
    echo "Attempting to recover by resetting alembic_version table..."
    echo "========================================="
    
    # First, try to drop the alembic_version table to clear stale references
    echo "Clearing stale migration history..."
    python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.session import ASYNC_DATABASE_URL

async def reset_alembic():
    # Use ASYNC_DATABASE_URL which is correctly configured in session.py
    engine = create_async_engine(ASYNC_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute(sa.text('DROP TABLE IF EXISTS alembic_version CASCADE;'))
        print('Dropped alembic_version table')
    await engine.dispose()

import sqlalchemy as sa
asyncio.run(reset_alembic())
" 2>&1 || echo "Could not drop alembic_version (might not exist)"
    
    # Now stamp with the current head
    echo "Stamping database with current head: b891cb8863b5"
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
        echo "ERROR: Failed to stamp database. Trying full migration from scratch..."
        # Last resort: try to run upgrade head which will create tables from scratch
        alembic -c /app/alembic.ini upgrade head
        if [ $? -ne 0 ]; then
            echo "ERROR: All migration recovery attempts failed. Exiting..."
            exit 1
        fi
    fi
elif grep -q "ERROR" /tmp/alembic_output.log; then
    echo "❌ Migration encountered errors. Exiting to prevent broken state..."
    exit 1
fi

# Cleanup
rm -f /tmp/alembic_output.log

# Start application
echo "========================================="
echo "Starting FastAPI application..."
echo "========================================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir app
