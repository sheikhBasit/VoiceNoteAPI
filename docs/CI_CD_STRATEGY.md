# VoiceNote API - CI/CD Strategy & Implementation Guide

**Last Updated:** February 6, 2026  
**Version:** 1.0  
**Purpose:** Establish a professional, automated deployment pipeline for solo development with fast feedback loops.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Git Workflow](#git-workflow)
3. [Environment Structure](#environment-structure)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Local Development](#local-development)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Process](#deployment-process)
8. [Monitoring & Rollback](#monitoring--rollback)
9. [Quick Reference](#quick-reference)

---

## 🎯 Overview

### Current State
- ⚠️ Manual deployments on every commit
- ❌ No staging environment
- ⚠️ High risk of production issues
- ❌ Limited visibility into deployment status

### Target State
```
Local Dev → Feature Branch → PR Tests → Merge to Develop
    ↓           ↓                ↓              ↓
  Fast      Auto-tested     Verified      Auto-deploy
  Loop      on Push       to Staging      to Staging
                                             ↓
                                    Manual Test/Verify
                                             ↓
                                   Tag Release (v1.0.0)
                                             ↓
                                    Auto-deploy to Prod
```

### Benefits
✅ **Safety** - No direct production deployments  
✅ **Speed** - Automated testing & deployment  
✅ **Rollback** - Single `git revert` command  
✅ **Visibility** - GitHub Actions provides full audit trail  
✅ **Scalability** - Ready for team expansion  

---

## 🌿 Git Workflow

### Branch Structure

```
main (production-ready)
  ├─ Tag: v1.0.0 → Deploy to Production
  ├─ Tag: v1.0.1 → Deploy to Production
  └─ Tag: v1.0.2 → Deploy to Production

staging (pre-release testing)
  ├─ Auto-deploys to staging environment
  └─ Merged from develop when ready to test

develop (development integration)
  ├─ Default integration branch
  ├─ Auto-deploys to dev environment
  └─ Feature branches merge here

feature/* (feature branches)
  ├─ feature/notes-api-fixes
  ├─ feature/admin-dashboard
  └─ feature/performance-optimization
```

### Step-by-Step Workflow

#### 1️⃣ **Start Feature Development**
```bash
# Update develop branch
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/my-feature-name develop

# Make changes
git add .
git commit -m "feat: add new feature"

# Push to GitHub
git push origin feature/my-feature-name
```

#### 2️⃣ **Create Pull Request & Automated Testing**
```bash
# On GitHub:
# 1. Go to https://github.com/yourname/VoiceNoteAPI
# 2. Click "New Pull Request"
# 3. Base: develop, Compare: feature/my-feature-name
# 4. Add description & submit

# Automatic Actions (GitHub Actions runs):
# ✅ Unit Tests
# ✅ Integration Tests
# ✅ Code Quality Checks
# ✅ Security Scan
# → Check Results in PR (green checkmark = all pass)
```

#### 3️⃣ **Merge to Develop (Auto-deploys to Dev)**
```bash
# After PR approved:
# Click "Merge Pull Request" on GitHub

# Or command line:
git checkout develop
git merge --no-ff feature/my-feature-name
git push origin develop

# Auto Deployment to DEV happens immediately
# Verify: curl https://dev-api.your-domain.com/health
```

#### 4️⃣ **Merge Develop → Staging (Manual Testing)**
```bash
# When feature is verified in develop:
git checkout staging
git pull origin staging
git merge develop
git push origin staging

# Auto Deployment to STAGING happens
# Manual Testing Phase:
# - Test features: https://staging-api.your-domain.com
# - Run integration tests
# - Check logs for errors
# ✅ Approve if everything works
```

#### 5️⃣ **Release to Production (Tag Release)**
```bash
# Create annotated tag (triggers production deployment)
git checkout main
git pull origin main
git merge staging
git tag -a v1.0.0 -m "Release v1.0.0: Feature X + Bug fixes"
git push origin main
git push origin v1.0.0

# Production deployment happens automatically
# Monitor: curl https://api.your-domain.com/health
```

#### 6️⃣ **Hotfix (Emergency Production Fix)**
```bash
# If critical bug in production:
git checkout -b hotfix/critical-bug main
# ... fix code ...
git add .
git commit -m "hotfix: fix critical bug"
git push origin hotfix/critical-bug

# Create PR against main
# Merge to main
git tag -a v1.0.1 -m "Hotfix v1.0.1"
git push origin v1.0.1

# Production deploys immediately
```

---

## 🏗️ Environment Structure

### Three Environment Strategy

| Environment | Branch | Use Case | Auto-Deploy |
|-------------|--------|----------|-------------|
| **DEV** | `develop` | Rapid development, breaking changes OK | ✅ Every push |
| **STAGING** | `staging` | Pre-release testing, mirrors production | ✅ On merge |
| **PRODUCTION** | `main` + tag | Live users, max stability | ✅ On tag |

### Environment Separation

```yaml
# .env.dev
DATABASE_URL=postgresql://dev:dev@db:5432/voicenote_dev
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=DEBUG
ENABLE_PROFILING=true

# .env.staging
DATABASE_URL=postgresql://staging:staging@staging-db:5432/voicenote
REDIS_URL=redis://staging-redis:6379/0
LOG_LEVEL=INFO
ENABLE_PROFILING=false

# .env.production
DATABASE_URL=postgresql://prod:prod@prod-db:5432/voicenote
REDIS_URL=redis://prod-redis:6379/0
LOG_LEVEL=WARNING
ENABLE_PROFILING=false
```

---

## 🔄 CI/CD Pipeline

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GitHub Actions                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. PULL REQUEST → Auto-test all commits               │
│     ├─ Lint & Format Check                             │
│     ├─ Unit Tests                                       │
│     ├─ Integration Tests                               │
│     ├─ Security Scan                                   │
│     └─ Coverage Report                                 │
│                                                         │
│  2. PUSH to develop → Deploy to DEV                    │
│     ├─ Run all tests                                   │
│     ├─ Build Docker image                              │
│     └─ Deploy to dev environment                       │
│                                                         │
│  3. PUSH to staging → Deploy to STAGING                │
│     ├─ Run all tests                                   │
│     ├─ Build Docker image                              │
│     └─ Deploy to staging environment                   │
│                                                         │
│  4. TAG (v*) → Deploy to PRODUCTION                    │
│     ├─ Run all tests                                   │
│     ├─ Build Docker image                              │
│     ├─ Push to registry                                │
│     └─ Deploy to production environment                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Test Categories

#### 🚀 **Fast Tests (CI - 2-3 minutes)**
- Unit tests
- Fast integration tests
- Code quality checks
- Security scans

```bash
pytest tests/test_core.py -v  # ~30 sec
pytest tests/test_main.py -v  # ~30 sec
flake8 app/                    # ~10 sec
bandit -r app/                 # ~20 sec
```

#### 🔍 **Medium Tests (On Merge - 5-10 minutes)**
- Full integration tests
- E2E API tests
- Admin system tests
- Coverage reports

```bash
pytest tests/ -v --cov=app    # ~5 min
```

#### 🏋️ **Heavy Tests (Manual - 15+ minutes)**
- Load testing
- Performance benchmarking
- Security penetration testing
- Full regression suite

```bash
pytest tests/ -m load -v      # ~10 min
locust -f tests/locustfile.py # ~15 min
```

---

## 💻 Local Development

### Setup (First Time)

```bash
# 1. Clone repository
git clone https://github.com/yourname/VoiceNoteAPI.git
cd VoiceNoteAPI

# 2. Create develop branch locally (if not exists)
git checkout develop
git pull origin develop

# 3. Install development dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Setup pre-commit hooks
chmod +x scripts/pre-push-check.sh
cp scripts/pre-push-check.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# 5. Start containers
make dev
```

### Daily Development Workflow

```bash
# 1. Start develop
source venv/bin/activate
make dev

# 2. Create feature branch
git checkout -b feature/my-feature develop

# 3. Edit code & test frequently
# ... make changes ...
pytest tests/test_core.py -v  # Quick test

# 4. Before push: run all local checks
pytest tests/ -v                # Full tests
make format                      # Auto-format code
make lint                        # Check quality

# 5. Push feature
git add .
git commit -m "feat: description"
git push origin feature/my-feature

# 6. Create PR on GitHub & wait for auto-tests
```

### Useful Make Commands

```bash
make help           # Show all available commands
make dev            # Start development environment
make up             # Start all services
make down           # Stop all services
make restart        # Restart services
make logs           # Follow all logs
make logs-api       # Follow API logs only
make test           # Run all tests
make test-quick     # Run fast tests only (unit + quick integration)
make lint           # Check code quality
make format         # Auto-format code
make clean          # Clean temporary files
make health         # Health check all services
```

---

## 🧪 Testing Strategy

### Test File Organization

```
tests/
├─ test_core.py              # Unit tests (fast) ⚡
├─ test_main.py              # Main endpoint tests ⚡
├─ test_new_endpoints.py      # API endpoint tests ⚡
├─ test_admin_system.py       # Admin feature tests ⚡
├─ test_audio.py             # Audio processing tests ⚡
├─ conftest.py               # Pytest configuration
├─ conftest_advanced.py       # Advanced fixtures
│
├─ test_enterprise_suite.py   # Integration tests 🟡
├─ test_comprehensive_500_part1.py
│
├─ test_load_concurrent.py    # Load tests 🔴
├─ test_advanced_performance.py
├─ locustfile.py             # Locust performance tests
│
└─ scenarios/                 # Test scenarios
```

### Test Markers

```bash
# Run only fast tests (for quick development)
pytest -m "not load and not stress" -v

# Run unit + integration tests (for CI)
pytest -m "not load and not stress and not performance" -v

# Run all tests (for CD/before production)
pytest tests/ -v

# Run specific category
pytest -m load -v              # Load tests only
pytest -m security -v          # Security tests only
```

### Coverage Requirements

```bash
# Check coverage for app module
pytest --cov=app --cov-report=html tests/

# Minimum 70% coverage required for merge
pytest --cov=app --cov-fail-under=70 tests/
```

---

## 🚀 Deployment Process

### Automatic Deployments

#### **Develop Branch → Dev Environment**
```yaml
Trigger: Any push to develop
Action:
  1. Run all tests
  2. Build Docker image
  3. Deploy to dev server
  4. Health check
Status: Visible in GitHub Actions
```

#### **Staging Branch → Staging Environment**
```yaml
Trigger: Any push to staging
Action:
  1. Run all tests
  2. Build Docker image
  3. Deploy to staging server
  4. Health check
  5. Slack notification
Status: Visible in GitHub Actions
```

#### **Tag Release → Production**
```yaml
Trigger: git tag -a vX.Y.Z && git push origin vX.Y.Z
Action:
  1. Run all tests
  2. Build Docker image
  3. Push to registry
  4. Deploy to production (blue-green)
  5. Health check & smoke tests
  6. Slack notification
Status: Visible in GitHub Actions
```

### Manual Deployment (If Needed)

```bash
# If automatic deployment fails, manual deploy:

# SSH to server
ssh deploy@your-server.com

# Stop old service
cd voicenote-api
docker-compose down

# Pull latest code
git fetch origin
git checkout v1.0.0

# Start new service
docker-compose up -d
docker-compose exec api alembic upgrade head

# Verify
curl http://localhost:8000/health
```

---

## 🔍 Monitoring & Rollback

### Health Checks

```python
# app/main.py
from datetime import datetime
import os

@app.get("/health")
def health_check():
    """Health check endpoint with deployment info"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("DEPLOYMENT_VERSION", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "unknown"),
        "deployed_at": os.getenv("DEPLOYMENT_TIME", "unknown")
    }

@app.get("/ready")
def readiness_check():
    """Readiness check for load balancer"""
    # Check database
    # Check Redis
    # Check external services
    return {"ready": True}
```

### Monitoring Commands

```bash
# Check deployment status
curl https://api.your-domain.com/health | jq

# View logs
docker-compose logs -f api

# Check GitHub Actions status
# Visit: https://github.com/yourname/VoiceNoteAPI/actions
```

### Quick Rollback

If something goes wrong in production:

```bash
# Method 1: Git Revert (Recommended)
git log --oneline -5
git revert <commit-hash>
git push origin main
git tag -a v1.0.1-revert -m "Rollback to v1.0.0"
git push origin v1.0.1-revert

# Method 2: Direct Tag
git tag -a v1.0.0 -m "Emergency rollback" <previous-commit-hash>
git push origin v1.0.0 --force

# Method 3: Manual (If GitHub Actions is down)
ssh deploy@your-server.com
cd voicenote-api
git checkout v1.0.0
docker-compose down && docker-compose up -d
```

### Alerts & Monitoring

Setup alerts for:
- ❌ Failed deployments
- 🔴 API errors (5xx responses)
- ⚠️ High latency
- 💥 Out of memory
- 📊 High CPU usage

---

## 📝 Quick Reference

### Command Cheatsheet

#### **Feature Development**
```bash
# Start new feature
git checkout -b feature/my-feature develop
git push origin feature/my-feature
# → Create PR on GitHub → Auto-test

# Merge feature
git checkout develop
git merge feature/my-feature
git push origin develop
# → Auto-deploy to dev
```

#### **Staging Release**
```bash
# Prepare staging
git checkout staging
git merge develop
git push origin staging
# → Auto-deploy to staging
# → Manual testing phase
```

#### **Production Release**
```bash
# Release to production
git checkout main
git merge staging
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin main v1.0.0
# → Auto-deploy to production
```

#### **Quick Testing**
```bash
pytest -m "not load and not stress" -v  # Fast tests
pytest tests/test_core.py -v             # Specific test
pytest --cov=app -v tests/               # With coverage
make test                                # Full suite
```

#### **Code Quality**
```bash
make format          # Auto-format code
make lint            # Check quality
flake8 app/          # Lint only
bandit -r app/       # Security scan
```

### File Locations

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI/CD pipeline definition |
| `.github/workflows/deploy.yml` | Production deployment |
| `Makefile` | Local development commands |
| `scripts/pre-push-check.sh` | Pre-push validation |
| `pytest.ini` | Pytest configuration |
| `requirements.txt` | Python dependencies |
| `.env.dev` | Dev environment variables |
| `.env.staging` | Staging environment variables |

### GitHub Actions Status

Check at: `https://github.com/yourname/VoiceNoteAPI/actions`

- 🟢 Green = All tests passed
- 🔴 Red = Tests failed
- 🟡 Yellow = Running
- ⚪ Skipped = Condition not met

---

## 🎓 Decision Points

### When to Merge to Develop?
✅ All CI tests pass  
✅ Code reviewed (if pair programming)  
✅ No conflicts  

### When to Merge to Staging?
✅ Feature is complete in develop  
✅ Integration tests pass  
✅ Ready for manual testing  

### When to Release to Production?
✅ Tested in staging  
✅ All edge cases verified  
✅ Rollback plan ready  
✅ No active incidents  

---

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Git Workflow Guide](https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Pytest Documentation](https://docs.pytest.org/)

---

## ✅ Implementation Checklist

- [ ] Create `.github/workflows/ci.yml` (fast tests on PR)
- [ ] Update `.github/workflows/deploy.yml` (deploy on tag)
- [ ] Create `scripts/pre-push-check.sh` (local validation)
- [ ] Create `requirements-dev.txt` (dev dependencies)
- [ ] Update `Makefile` with new commands
- [ ] Setup environment variables in GitHub Secrets
- [ ] Create `.env.dev`, `.env.staging` templates
- [ ] Add health check endpoint
- [ ] Test workflow with a feature branch
- [ ] Document deployment procedures
- [ ] Setup monitoring/alerts

---

**Version History:**
- v1.0 - Initial CI/CD strategy document (Feb 6, 2026)

