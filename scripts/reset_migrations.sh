#!/bin/bash

# Script to reset Alembic migrations when encountering "Can't locate revision" errors
# This is useful when you've squashed migrations or rebased branches

set -e

echo "========================================="
echo "Alembic Migration Reset Tool"
echo "========================================="
echo ""
echo "This script will:"
echo "1. Drop the alembic_version table"
echo "2. Stamp the database with the current head revision"
echo "3. Run migrations from the current state"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Dropping alembic_version table..."
docker compose exec -T db psql -U postgres -d postgres -c "DROP TABLE IF EXISTS alembic_version CASCADE;" || {
    echo "Warning: Could not drop alembic_version table (might not exist)"
}

echo ""
echo "Step 2: Getting current head revision..."
CURRENT_HEAD=$(docker compose exec -T api alembic -c /app/alembic.ini heads | grep -oP '^[a-f0-9]+' | head -n1)
echo "Current head revision: $CURRENT_HEAD"

echo ""
echo "Step 3: Stamping database with head revision..."
docker compose exec -T api alembic -c /app/alembic.ini stamp "$CURRENT_HEAD"

echo ""
echo "Step 4: Running migrations..."
docker compose exec -T api alembic -c /app/alembic.ini upgrade head

echo ""
echo "Step 5: Verifying migration status..."
docker compose exec -T api alembic -c /app/alembic.ini current

echo ""
echo "========================================="
echo "Migration reset completed successfully!"
echo "========================================="
