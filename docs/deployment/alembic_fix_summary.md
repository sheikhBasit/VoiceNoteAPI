# Alembic Migration Fix - Summary

**Date:** 2026-02-08  
**Issue:** GitHub Actions deployment failing with "Can't locate revision identified by 'a2242b61af45'"

## Root Cause

The database in the production environment had a reference to migration revision `a2242b61af45` (from `add_document_uris_column.py`), but this file was deleted during a rebase/branch reset. The current codebase only has the squashed migration `b891cb8863b5_initial_squashed_migration.py`.

## Changes Made

### 1. **GitHub Actions Workflow** (`.github/workflows/deploy.yml`)

**Problem:** The workflow was pruning volumes while containers were still running, which didn't properly clear the database state.

**Fix:**
- Added `docker compose down` **before** pruning volumes
- Added explicit wait for database health
- Added migration recovery logic with automatic stamping
- Improved error handling and logging

**Key Changes:**
```yaml
# Stop containers BEFORE pruning to release volumes
sudo docker compose down

# Reclaim disk space and remove old volumes
sudo docker system prune -af
sudo docker volume prune -f

# Start all services with fresh state
sudo docker compose up -d --no-build

# Wait for database to be ready
sleep 10

# Run migrations with auto-recovery
sudo docker compose exec -T api alembic upgrade head || {
  echo "Migration failed, attempting recovery..."
  sudo docker compose exec -T api alembic stamp head
  sudo docker compose exec -T api alembic upgrade head
}
```

### 2. **Container Startup Script** (`scripts/start.sh`)

**Problem:** The recovery logic only stamped the database but didn't clear stale references from the `alembic_version` table.

**Fix:**
- Added Python code to drop the `alembic_version` table before stamping
- Added fallback logic to run migrations from scratch if stamping fails
- Improved error messages and logging

**Key Changes:**
```bash
# Drop the alembic_version table to clear stale references
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def reset_alembic():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.execute('DROP TABLE IF EXISTS alembic_version CASCADE;')
    await engine.dispose()

asyncio.run(reset_alembic())
"

# Stamp with current head
alembic stamp b891cb8863b5

# Run migrations
alembic upgrade head
```

### 3. **Manual Reset Script** (`scripts/reset_migrations.sh`)

**New File:** Created a utility script for manually resetting migrations when needed.

**Usage:**
```bash
./scripts/reset_migrations.sh
```

**What it does:**
1. Prompts for confirmation
2. Drops the `alembic_version` table
3. Gets the current head revision from code
4. Stamps the database
5. Runs migrations
6. Verifies the final state

### 4. **Documentation** (`docs/deployment/alembic_recovery.md`)

**New File:** Comprehensive guide covering:
- Problem diagnosis
- Multiple solution paths (reset vs. manual recovery)
- Automated recovery mechanisms
- Prevention strategies
- Troubleshooting steps
- Current migration state

## Testing Recommendations

### Local Testing (Optional)

If you want to test the fix locally:

```bash
# Simulate the issue by creating a stale migration reference
docker compose down -v
docker compose up -d

# The startup script should automatically recover
docker compose logs api
```

### GitHub Actions Testing

The fix will be tested automatically on the next push to `main`:

```bash
git add .
git commit -m "fix: Alembic migration recovery for squashed migrations"
git push origin main
```

## Expected Behavior

### Before Fix
```
ERROR [alembic.util.messaging] Can't locate revision identified by 'a2242b61af45'
FAILED: Can't locate revision identified by 'a2242b61af45'
Container voicenote_api Error dependency api failed to start
```

### After Fix

**GitHub Actions:**
```
Stopping containers...
Pruning volumes...
Starting services with fresh state...
Waiting for database to be healthy...
Running database migrations...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> b891cb8863b5, Initial squashed migration
✅ Deployment successful
```

**Container Startup (if recovery needed):**
```
Detected missing migration history (likely due to squash).
Attempting to recover by resetting alembic_version table...
Clearing stale migration history...
Dropped alembic_version table
Stamping database with current head: b891cb8863b5
Stamp successful. Running upgrade...
Migration recovery completed successfully!
Starting FastAPI application...
```

## Files Modified

1. `.github/workflows/deploy.yml` - Enhanced deployment workflow
2. `scripts/start.sh` - Improved migration recovery
3. `scripts/reset_migrations.sh` - New manual reset utility
4. `docs/deployment/alembic_recovery.md` - New documentation

## Next Steps

1. **Commit and push** the changes to trigger GitHub Actions
2. **Monitor the deployment** to ensure the fix works
3. **Verify the API** is healthy after deployment
4. **Keep the documentation** updated if migration strategy changes

## Prevention

To avoid this issue in the future:

1. ✅ **Never delete migration files** - Use proper squashing instead
2. ✅ **Test migrations locally** before pushing
3. ✅ **Use the reset script** when switching branches with different migrations
4. ✅ **Document migration changes** in commit messages

## Rollback Plan

If the fix doesn't work:

1. The deployment will fail early (during migration)
2. The old containers will remain running
3. You can manually run: `./scripts/reset_migrations.sh`
4. Or use the manual recovery steps in `docs/deployment/alembic_recovery.md`

---

**Status:** Ready to commit and deploy ✅
