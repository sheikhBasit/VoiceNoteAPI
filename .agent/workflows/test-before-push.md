---
description: Mandatory test verification before any git push
---

# Test-Before-Push Workflow

This workflow ensures all tests pass before pushing code changes to the repository.

## Prerequisites

- Docker and Docker Compose installed
- All services running (`docker compose up -d`)

## Workflow Steps

### 1. Run Full Test Suite
```bash
make test
```

**Expected Outcome**: All tests should pass with exit code 0.

### 2. If Tests Fail

**DO NOT PUSH**. Instead:

a) Identify failing tests from output
b) Run specific test file to debug:
```bash
docker compose run --rm -T -e PYTHONPATH=/app api python -m pytest tests/test_<module>.py -vv
```

c) Fix the issues in the code
d) Re-run full test suite (step 1)

### 3. Verify Critical Modules

Before pushing changes to specific modules, verify their tests:

**For API Changes:**
```bash
docker compose run --rm -T -e PYTHONPATH=/app api python -m pytest tests/test_niche_2026.py tests/test_new_endpoints.py -v
```

**For Service Changes:**
```bash
docker compose run --rm -T -e PYTHONPATH=/app api python -m pytest tests/test_audit_logic_2.py tests/test_niche_logic.py -v
```

**For Database Changes:**
```bash
docker compose run --rm -T -e PYTHONPATH=/app api python -m pytest tests/v_model/ -v
```

### 4. Check for Regressions

Run the most recent failing tests to ensure your changes didn't reintroduce bugs:
```bash
docker compose run --rm -T -e PYTHONPATH=/app api python -m pytest tests/test_niche_logic.py tests/test_new_endpoints.py -v
```

### 5. Only After All Tests Pass

```bash
git add .
git commit -m "Your commit message"
git push
```

## Quick Reference

| Command | Purpose |
|---------|---------|
| `make test` | Run all tests |
| `make test-specific FILE=test_file.py` | Run specific test file |
| `docker compose logs api` | View API logs for debugging |
| `docker compose down && docker compose up -d` | Restart services |

## Notes

- Tests run in isolated Docker containers with fresh database state
- All AI services are mocked in tests (no real API keys needed)
- Test failures often indicate breaking changes - review carefully before proceeding
