---
description: Manual CI/CD Pipeline Setup without GitHub Actions
---

# Manual CI/CD Pipeline

This workflow describes how to use the local CI/CD setup created for VoiceNote API.

## 1. Continuous Integration (CI)
**Mechanism**: Git Pre-push Hook
**Location**: `.git/hooks/pre-push`

automatically runs whenever you `git push`.
- Triggers `make test`.
- If tests pass: Push continues.
- If tests fail: Push is aborted.

**To bypass (emergency only):**
```css
git push --no-verify
```

## 2. Continuous Deployment (CD)
**Mechanism**: Shell Script
**Location**: `scripts/deploy.sh`

This script syncs your local code to the production server and restarts the Docker containers.

**Usage:**
```css
./scripts/deploy.sh [user@server_ip]
```

**Example:**
```css
./scripts/deploy.sh root@4.240.96.60
```

**Prerequisites:**
- SSH access to the server.
- Docker and Make installed on the server.
- `rsync` installed on both local and server.
