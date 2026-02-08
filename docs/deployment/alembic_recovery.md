# Alembic Migration Recovery Guide

## Problem: "Can't locate revision identified by 'a2242b61af45'"

This error occurs when Alembic tries to find a migration file that no longer exists in your repository. This commonly happens when:

1. **Migration file deleted or renamed** - You created a migration, then rebased/reset and the file was removed
2. **Different DB volume than expected** - Local DB volume contains old migration history, but CI container has fresh code
3. **Multiple branches created migrations independently** - Classic Alembic divergence problem

## Quick Diagnosis

Check if the migration file exists:
```bash
ls alembic/versions | grep a2242b61af45
```

If it's missing, you have a mismatch between your database state and your codebase.

## Solutions

### Option A: Reset Database (Recommended for Dev/CI)

**Best for:** GitHub Actions, local development, or any environment where data can be lost.

```bash
# Stop all containers and remove volumes
docker compose down -v

# Start fresh
docker compose up --build
```

This is the **cleanest solution** and is now automated in the GitHub Actions workflow.

### Option B: Manual Migration Reset (For Staging/Production)

**Best for:** Environments where you need to preserve data.

Use the provided reset script:

```bash
./scripts/reset_migrations.sh
```

Or manually:

```bash
# 1. Check current DB revision
docker exec -it voicenote_db psql -U postgres -d postgres -c \
  "SELECT version_num FROM alembic_version;"

# 2. Drop the alembic_version table
docker exec -it voicenote_db psql -U postgres -d postgres -c \
  "DROP TABLE IF EXISTS alembic_version CASCADE;"

# 3. Get current head revision from code
docker compose exec api alembic -c /app/alembic.ini heads

# 4. Stamp database with current head (replace with actual revision)
docker compose exec api alembic -c /app/alembic.ini stamp b891cb8863b5

# 5. Run migrations
docker compose exec api alembic -c /app/alembic.ini upgrade head
```

## Automated Recovery

The system now has **automatic recovery** built into:

### 1. GitHub Actions Deployment (`deploy.yml`)

The workflow now:
- Stops containers **before** pruning volumes
- Removes all volumes to ensure fresh state
- Includes migration recovery logic with automatic stamping

### 2. Container Startup (`scripts/start.sh`)

The startup script automatically:
- Detects "Can't locate revision" errors
- Drops the `alembic_version` table
- Stamps the database with the current head
- Retries the migration

## Prevention

To avoid this issue in the future:

1. **Never delete migration files** - If you need to consolidate, use proper squashing
2. **Use consistent branches** - Avoid creating migrations on multiple branches simultaneously
3. **Test migrations locally** before pushing to CI/CD
4. **Use the reset script** when switching between branches with different migration histories

## Verification

After recovery, verify the migration state:

```bash
# Check current revision
docker compose exec api alembic -c /app/alembic.ini current

# Check migration history
docker compose exec api alembic -c /app/alembic.ini history

# Verify database tables exist
docker exec voicenote_db psql -U postgres -d postgres -c "\dt"
```

## Current Migration State

As of 2026-02-08, the repository has a **single squashed migration**:

- **Revision ID:** `b891cb8863b5`
- **File:** `alembic/versions/b891cb8863b5_initial_squashed_migration.py`
- **Down Revision:** `None` (this is the first/only migration)

This migration creates all tables from scratch, including:
- Users, Organizations, Service Plans
- Notes, Folders, Tasks
- Wallets, Transactions
- API Keys, Refresh Tokens
- And all supporting tables

## Troubleshooting

### Error: "relation 'alembic_version' does not exist"

This is **normal** for a fresh database. The `alembic_version` table is created automatically when you run migrations for the first time.

### Error: Container is unhealthy

Check the logs:
```bash
docker compose logs api
```

The startup script should show the migration recovery process.

### Error: Migration still fails after recovery

1. Check if the database has any tables:
   ```bash
   docker exec voicenote_db psql -U postgres -d postgres -c "\dt"
   ```

2. If tables exist but migration fails, you may need to manually drop all tables:
   ```bash
   docker compose down -v
   docker compose up -d
   ```

## Related Files

- **Migration file:** `/alembic/versions/b891cb8863b5_initial_squashed_migration.py`
- **Startup script:** `/scripts/start.sh`
- **Reset script:** `/scripts/reset_migrations.sh`
- **GitHub Actions:** `/.github/workflows/deploy.yml`
- **This guide:** `/docs/deployment/alembic_recovery.md`
