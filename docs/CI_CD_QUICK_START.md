# VoiceNote API - Quick Start Guide for CI/CD Implementation

**Last Updated:** February 6, 2026  
**Purpose:** Get you up and running with the new CI/CD workflow in minutes

---

## 📋 Prerequisites

Before starting, make sure you have:

- ✅ Git (v2.30+)
- ✅ Docker & Docker Compose
- ✅ Python 3.11+
- ✅ GitHub Account with access to VoiceNoteAPI repo
- ✅ SSH access to your server (for deployments)

---

## 🚀 PHASE 1: Initial Setup (First Time Only)

### Step 1: Clone & Setup Local Environment

```bash
# 1. Clone the repository
git clone https://github.com/yourname/VoiceNoteAPI.git
cd VoiceNoteAPI

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Install git hooks for pre-push validation
make install-hooks

# 5. Copy environment templates
cp .env.dev.example .env
cp .env.staging.example .env.staging
cp .env.production.example .env.production

# 6. Edit .env file with your local credentials
nano .env  # Add your API keys, database credentials, etc.
```

### Step 2: Start Development Environment

```bash
# Start all services (PostgreSQL, Redis, API)
make dev

# You should see:
# ✅ Database (PostgreSQL): ready
# ✅ Redis: ready
# ✅ API: running on http://localhost:8000
```

### Step 3: Create GitHub Secrets for CI/CD

Go to: `https://github.com/yourname/VoiceNoteAPI/settings/secrets/actions`

Add these secrets:

```yaml
# Deployment Keys
DEV_DEPLOY_KEY=<your-dev-server-private-key>
DEV_HOST=<dev-server-ip-or-domain>
DEV_USER=<dev-server-username>

STAGING_DEPLOY_KEY=<your-staging-server-private-key>
STAGING_HOST=<staging-server-ip-or-domain>
STAGING_USER=<staging-server-username>

PROD_DEPLOY_KEY=<your-prod-server-private-key>
PROD_SERVER_HOST=<prod-server-ip-or-domain>
PROD_SERVER_USER=<prod-server-username>
PROD_SSH_KEY=<your-prod-ssh-key>

# Docker Registry
DOCKERHUB_USERNAME=<your-docker-username>
DOCKERHUB_TOKEN=<your-docker-access-token>

# API Domain
PROD_API_DOMAIN=your-domain.com
```

**How to generate SSH keys:**
```bash
# Generate new SSH key
ssh-keygen -t ed25519 -C "voicenote-deploy" -f deploy_key

# Add public key to server's ~/.ssh/authorized_keys
ssh-copy-id -i deploy_key.pub user@server
```

---

## 💻 PHASE 2: Daily Development Workflow

### Starting Your Day

```bash
# 1. Update develop branch
git checkout develop
git pull origin develop

# 2. Start development environment
make dev

# 3. Create feature branch
git checkout -b feature/my-feature-name develop
```

### During Development

```bash
# Edit code
# Run tests frequently
make test-quick      # Fast local tests (~2 min)

# Format code
make format          # Auto-format
make lint            # Check quality

# Commit changes
git add .
git commit -m "feat: description of what you did"

# Check if pre-push hooks pass
git push origin feature/my-feature-name
```

### After Pushing

GitHub Actions automatically runs:
- ✅ Unit tests
- ✅ Integration tests  
- ✅ Code quality checks
- ✅ Security scan

**Check results:** Go to `https://github.com/yourname/VoiceNoteAPI/actions`

---

## 📝 PHASE 3: Merge Flow & Deployments

### Creating a Pull Request

```bash
# On GitHub:
# 1. Go to https://github.com/yourname/VoiceNoteAPI
# 2. Click "Compare & pull request"
# 3. Base: develop, Compare: your feature branch
# 4. Add description & submit

# Automatic tests run
# ✅ All tests passed? → Merge
# ❌ Tests failed? → Fix and push again
```

### Merging to Develop (Auto-deploys to Dev)

```bash
# After PR approved, click "Merge Pull Request" on GitHub
# OR use command line:

git checkout develop
git merge feature/my-feature-name
git push origin develop

# ✅ Automatically deployed to dev environment
# Verify: curl https://dev-api.your-domain.com/health
```

### Testing in Staging

```bash
# When develop is stable and ready for testing:
git checkout staging
git merge develop
git push origin staging

# ✅ Automatically deployed to staging
# Manual testing phase:
# - Visit: https://staging-api.your-domain.com
# - Run through feature checklist
# - Verify all integrations work
```

### Release to Production

```bash
# When staging is verified:
git checkout main
git merge staging
git push origin main

# Create release tag:
git tag -a v1.0.0 -m "Release v1.0.0: Added feature X, fixed bug Y"
git push origin v1.0.0

# ✅ Automatically deployed to production
# Monitor: https://github.com/yourname/VoiceNoteAPI/actions
```

---

## 🆘 Quick Troubleshooting

### Tests Failing Locally?

```bash
# Make sure you're in the venv
source venv/bin/activate

# Start services
make up

# Run tests
make test-quick

# Check logs
make logs-api
```

### Need to Rollback?

```bash
# If production is broken:
git revert <bad-commit-hash>
git push origin main

# Create hotfix tag
git tag -a v1.0.1-hotfix -m "Emergency rollback"
git push origin v1.0.1-hotfix

# Or manually redeploy previous version:
git tag -a v1.0.0 -m "Manual rollback" <previous-commit-hash>
git push origin v1.0.0 --force
```

### Clean Everything & Start Fresh?

```bash
# Stop all services
make down

# Remove data
docker system prune -af

# Start fresh
make fresh-start
```

---

## 📚 Useful Commands Cheatsheet

```bash
# DEVELOPMENT
make dev              # Start development environment
make format           # Auto-format code
make lint             # Check code quality

# TESTING
make test-quick       # Fast tests (~2 min)
make test             # All tests (~5-10 min)
make test-coverage    # Tests with coverage report

# DEBUGGING
make logs             # View all logs
make logs-api         # View API logs only
make shell            # Open API container shell
make db-shell         # Open database shell

# DEPLOYMENT (via Git)
git push origin feature/name          # → Auto-test in CI
git merge to develop                  # → Auto-deploy to dev
git merge develop → staging           # → Auto-deploy to staging  
git tag v1.0.0 && git push origin v1.0.0  # → Auto-deploy to prod

# DATABASE
make seed             # Seed database
make db-reset         # Reset database completely
make db-backup        # Backup database
```

---

## 🔄 Environment Overview

| Environment | Branch | Auto-Deploy | Purpose |
|-------------|--------|-------------|---------|
| **DEV** | `develop` | ✅ On push | Rapid development |
| **STAGING** | `staging` | ✅ On push | Pre-release testing |
| **PROD** | `main` (tag) | ✅ On tag | Live users |

---

## 📊 Workflow Diagram

```
Your Computer
    ↓
Feature Branch → Push to GitHub
    ↓
GitHub Actions (CI)
    ├─ Unit Tests ✓
    ├─ Integration Tests ✓
    ├─ Code Quality ✓
    └─ Security Scan ✓
    ↓
Create PR & Merge to develop
    ↓
Auto-Deploy to DEV (5 min)
    ↓
Manual Merge to staging
    ↓
Auto-Deploy to STAGING (5 min)
    ↓
Manual Testing & Verification
    ↓
Create Release Tag (v1.0.0)
    ↓
Auto-Deploy to PRODUCTION (5 min)
    ↓
Monitor & Alert
```

---

## ✅ Implementation Checklist

- [ ] Clone repository and setup local environment
- [ ] Install git hooks (`make install-hooks`)
- [ ] Copy `.env` files and add credentials
- [ ] Start development environment (`make dev`)
- [ ] Test that services are healthy
- [ ] Create GitHub Secrets for CI/CD
- [ ] Test feature branch workflow (create dummy PR)
- [ ] Verify GitHub Actions runs tests
- [ ] Test merge to develop (auto-deploy to dev)
- [ ] Test merge to staging (auto-deploy to staging)
- [ ] Test release tag (auto-deploy to prod)
- [ ] Setup monitoring/alerts
- [ ] Document deployment procedures for team

---

## 🎓 Next Steps

1. **Read Full Documentation:** `docs/CI_CD_STRATEGY.md`
2. **Test Workflow:** Create a test feature branch and follow the workflow
3. **Setup Monitoring:** Add health checks and alerts
4. **Document Runbooks:** Create procedures for common scenarios
5. **Celebrate:** You now have professional CI/CD! 🎉

---

## 📞 Need Help?

Check logs:
```bash
make logs              # All logs
make logs-api          # API only
docker-compose logs -f # Raw output
```

Verify setup:
```bash
make health            # Health check
make status            # Service status
```

---

**Ready to deploy?** Follow the workflow in the [CI_CD_STRATEGY.md](CI_CD_STRATEGY.md) guide!
