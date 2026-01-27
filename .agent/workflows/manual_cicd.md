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
```bash
git push --no-verify
```

## 2. Continuous Deployment (CD - Push from Local)
**Mechanism**: Shell Script
**Location**: `scripts/deploy.sh`

This script syncs your local code to the production server and restarts the Docker containers.

**Usage:**
```bash
./scripts/deploy.sh
```

**Configuration:**
- **Key File**: `/home/basitdev/Downloads/voice_note_ai.pem`
- **Server**: `azureuser@4.240.96.60`
- **Remote Path**: `/home/azureuser/voicenote-api`

The script handles the SSH connection using the specified PEM key automatically.

## 3. Webhook-Based CD (Automated via GitHub)
**Mechanism**: Python Listener (`scripts/cicd_listener.py`)
**Concept**: GitHub sends a webhook -> Your Server receives it -> Triggers update script.

**Setup Instructions:**

1.  **On The Server (Azure VM):**
    *   Upload the scripts (or run `deploy.sh` once to sync them):
        ```bash
        ./scripts/deploy.sh
        ```
    *   SSH into the server:
        ```bash
        ssh -i /home/basitdev/Downloads/voice_note_ai.pem azureuser@4.240.96.60
        ```
    *   Start the listener (run in background/screen):
        ```bash
        cd voicenote-api
        python3 scripts/cicd_listener.py &
        ```
    *   **Important**: Ensure port `9000` is open in your Azure Network Security Group (NSG) for Inbound TCP.

2.  **On GitHub:**
    *   Go to repo **Settings** -> **Webhooks** -> **Add webhook**.
    *   **Payload URL**: `http://4.240.96.60:9000/webhook/deploy`
    *   **Content type**: `application/json`
    *   **Secret**: `replace_with_your_secure_random_token` (Match the token in `cicd_listener.py`)
    *   **Events**: Select "Just the push event".

3.  **Workflow:**
    *   You push code to GitHub.
    *   GitHub calls your listener.
    *   Listener runs `server_update.sh`: pulls code via Git and restarts Docker.
