# VoiceNote API - Deployment Checklist & Runbooks

**Purpose:** Quick reference for common deployment scenarios  
**Last Updated:** February 6, 2026

---

## 🚀 Feature Deployment Checklist

### Before Development
- [ ] Create feature branch: `git checkout -b feature/my-feature develop`
- [ ] Pull latest develop: `git pull origin develop`
- [ ] Create `.env` with your credentials
- [ ] Start development: `make dev`

### During Development
- [ ] Make code changes
- [ ] Run quick tests: `make test-quick`
- [ ] Format code: `make format`
- [ ] Check quality: `make lint`
- [ ] Commit: `git commit -m "feat: description"`

### Before Pushing
- [ ] All tests pass: `make test`
- [ ] Code formatted properly
- [ ] No hardcoded secrets
- [ ] Updated relevant documentation

### After Pushing
- [ ] Check GitHub Actions: `https://github.com/yourname/VoiceNoteAPI/actions`
- [ ] Verify all CI checks pass (green ✓)
- [ ] Create Pull Request with description
- [ ] Review code changes

### Merging to Develop (→ Dev Deployment)
- [ ] All tests pass in CI
- [ ] PR reviewed
- [ ] Click "Merge Pull Request" on GitHub
- [ ] Verify deployment: `curl https://dev-api.your-domain.com/health`

---

## 🌐 Staging Deployment Checklist

### Prepare for Staging
- [ ] Feature is complete and working in develop
- [ ] All tests pass
- [ ] Documentation updated
- [ ] No known issues

### Deploy to Staging
```bash
git checkout staging
git merge develop
git push origin staging
```

### Testing in Staging
- [ ] API health check: `curl https://staging-api.your-domain.com/health`
- [ ] All features working correctly
- [ ] Integration tests pass
- [ ] Database migrations successful
- [ ] No errors in logs: `ssh user@staging-server "docker-compose logs -f api"`
- [ ] Test with real data if possible
- [ ] Performance acceptable
- [ ] Security checks pass

### Sign-Off
- [ ] All manual testing complete
- [ ] No critical issues found
- [ ] Ready for production

---

## 🔴 Production Deployment Checklist

### Pre-Deployment
- [ ] Feature tested thoroughly in staging
- [ ] All tests pass
- [ ] Database migrations tested
- [ ] Rollback plan ready
- [ ] Team notified

### Create Release
```bash
git checkout main
git merge staging
git tag -a v1.0.0 -m "Release v1.0.0: Feature X, Fix Y"
git push origin main v1.0.0
```

### Monitor Deployment
- [ ] GitHub Actions running: `https://github.com/yourname/VoiceNoteAPI/actions`
- [ ] Tests passing
- [ ] Docker image building
- [ ] Deployment in progress
- [ ] Health checks passing

### Post-Deployment Verification
- [ ] API responding: `curl https://api.your-domain.com/health`
- [ ] All endpoints accessible
- [ ] No error rate increase
- [ ] Database migrations successful: `curl https://api.your-domain.com/admin/health/db`
- [ ] Logs show no errors
- [ ] Performance metrics normal
- [ ] All integrations working

### Sign-Off
- [ ] Production deployment successful
- [ ] Users can access service
- [ ] No incidents reported

---

## 🆘 Emergency Rollback Checklist

### If Something Goes Wrong
- [ ] Stop and assess severity
- [ ] Check error logs: `curl https://api.your-domain.com/health`
- [ ] Verify impact: traffic loss, data corruption, etc.
- [ ] Notify team

### Quick Rollback (Git)
```bash
# Find the previous working version
git log --oneline -10

# Revert to previous commit
git revert <bad-commit-hash>
git push origin main

# Create rollback tag
git tag -a v1.0.1-rollback -m "Rollback to previous version"
git push origin v1.0.1-rollback
```

### Manual Rollback (If Git Approach Fails)
```bash
ssh deploy@prod-server

# Stop services
cd voicenote-api
docker-compose down

# Checkout previous version
git fetch origin --tags
git checkout v1.0.0  # Previous working version

# Restart
docker-compose up -d
sleep 5

# Verify
curl http://localhost:8000/health
```

### Post-Rollback
- [ ] Verify production is stable
- [ ] Check all endpoints
- [ ] Monitor error rates
- [ ] Notify team that service is restored
- [ ] Prepare fix for the issue
- [ ] Plan re-deployment

---

## 🔧 Hotfix Deployment Checklist

### Create Hotfix
```bash
git checkout -b hotfix/critical-bug main
# Fix code
git add .
git commit -m "hotfix: fix critical bug"
git push origin hotfix/critical-bug
```

### Test Hotfix
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manually verify fix
- [ ] No side effects

### Deploy Hotfix
```bash
git checkout main
git merge hotfix/critical-bug
git tag -a v1.0.1 -m "Hotfix v1.0.1: Fix critical bug"
git push origin main v1.0.1
```

### Verify
- [ ] GitHub Actions running
- [ ] Production deployed successfully
- [ ] Bug is fixed
- [ ] No new issues introduced

---

## 📊 Health Check Commands

### Local Development
```bash
# Check all services
make health

# Check API
curl http://localhost:8000/health

# Check database
curl http://localhost:8000/admin/health/db

# View logs
make logs
make logs-api
make logs-worker
```

### Staging
```bash
# API Health
curl https://staging-api.your-domain.com/health

# Database Health  
curl https://staging-api.your-domain.com/admin/health/db

# SSH and check logs
ssh user@staging-server
docker-compose logs -f api
```

### Production
```bash
# API Health
curl https://api.your-domain.com/health

# Database Health
curl https://api.your-domain.com/admin/health/db

# SSH and check logs (only if necessary)
ssh deploy@prod-server
docker-compose logs -f api

# Monitor metrics (if applicable)
curl https://api.your-domain.com/metrics
```

---

## 🐛 Debugging Failed Deployments

### GitHub Actions Failure
1. Go to: `https://github.com/yourname/VoiceNoteAPI/actions`
2. Click on failed workflow
3. Click on failed job
4. Review error message and logs
5. Common issues:
   - Tests failing → Fix code and push again
   - Docker build failing → Check Dockerfile
   - SSH connection failing → Check secrets/keys
   - Database migration failing → Review migration script

### Production Deployment Failure
```bash
# SSH to server
ssh deploy@prod-server

# Check service status
docker-compose ps

# Check logs for errors
docker-compose logs api | tail -100

# Check database
docker-compose exec db psql -U postgres -d voicenote -c "SELECT version();"

# Check if migrations ran
docker-compose logs api | grep "alembic"
```

### Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Tests failing in CI | Code issue | Review test output, fix code, push again |
| Docker image not found | Build failure | Check Dockerfile, Docker logs |
| SSH connection refused | Wrong credentials | Verify SSH key, host, user in GitHub secrets |
| Database migration error | Migration script issue | Review migration, rollback if necessary |
| Out of disk space | Old images accumulating | Run `docker system prune -af` on server |
| High memory usage | Memory leak | Restart services, review logs |
| API not responding | Crash or network issue | Check logs, verify configuration |

---

## 📝 Post-Deployment Tasks

### After Every Production Deployment
- [ ] Verify health checks passing
- [ ] Monitor error rates for 10 minutes
- [ ] Check database transaction logs
- [ ] Verify backups completed
- [ ] Update deployment log/wiki
- [ ] Document any issues encountered
- [ ] Close related GitHub issues

### Weekly/Monthly
- [ ] Review error logs and metrics
- [ ] Check backup integrity
- [ ] Update documentation if needed
- [ ] Plan future improvements
- [ ] Review security scans

---

## 🎯 SLA & Recovery Time Targets

| Scenario | RTO | RPO |
|----------|-----|-----|
| Minor bug fix | 5 min | 0 min (no data loss) |
| Feature deployment | 10 min | 0 min (no data loss) |
| Rollback | 2 min | 0 min (no data loss) |
| Hotfix critical issue | 3 min | 0 min (no data loss) |
| Database disaster | 30 min | Last backup |

---

## 📞 Escalation Path

If deployment fails and you need help:

1. **Check logs** - `make logs`
2. **Check GitHub Actions** - See what failed
3. **Try local tests** - `make test-quick`
4. **Check server status** - `curl health-endpoint`
5. **Review recent changes** - `git log --oneline -5`
6. **Ask team** - Slack/email if available
7. **Rollback if necessary** - Don't hesitate to revert

---

## 🚨 Critical Issues Response

### API Down
```bash
# 1. Check status
curl https://api.your-domain.com/health

# 2. Check logs
ssh deploy@prod-server
docker-compose logs api | tail -50

# 3. Restart services
docker-compose restart api

# 4. If still down, rollback
git checkout v<last-working-version>
docker-compose down && docker-compose up -d

# 5. Verify
curl https://api.your-domain.com/health
```

### Database Issues
```bash
# 1. Check database health
curl https://api.your-domain.com/admin/health/db

# 2. Check disk space
ssh deploy@prod-server
docker-compose exec db df -h

# 3. Check connections
docker-compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"

# 4. Kill idle connections if needed
docker-compose exec db psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND xact_start < now() - interval '30 min';"
```

### Memory/CPU Issues
```bash
# 1. Check resource usage
docker-compose stats

# 2. Restart API service to free memory
docker-compose restart api

# 3. Scale workers if needed
docker-compose up -d --scale celery_worker=2

# 4. Monitor memory
docker-compose stats --no-stream
```

---

**Remember:** When in doubt, check the logs first! 📋

