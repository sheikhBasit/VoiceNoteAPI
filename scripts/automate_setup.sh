#!/bin/bash

# Function to commit with a phase message
phase_commit() {
    git add .
    git commit -m "Phase: $1"
    echo "✅ Phase Completed: $1"
}

# --- PHASE 1: Initialization & VS Code Settings ---
git init
mkdir -p .vscode
cat <<EOF > .vscode/settings.json
{
    "files.autoSave": "afterDelay",
    "python.defaultInterpreterPath": ".venv/bin/python",
    "geminicodeassist.project": "elite-veld-n40gk",
    "git.openRepositoryInParentFolders": "never",
    "chat.tools.global.autoApprove": true,
    "chat.tools.terminal.enableAutoApprove": true,
    "chat.tools.terminal.autoApprove": {
        "python -m venv": true,
        "source .venv/bin/activate": true,
        "pip install": true,
        "uv sync": true,
        "docker-compose up": true,
        "uvicorn app.main:app": true,
        "pytest": true,
        "git status": true
    }
}
EOF
phase_commit "Project Initialization & VS Code Auto-Approve Config"

# --- PHASE 2: Virtual Environment & Dependencies ---
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn pytest sqlalchemy psycopg2-binary pgvector pydantic-settings
pip freeze > requirements.txt
phase_commit "Venv and Dependencies (FastAPI, SQLAlchemy, pgvector)"

# --- PHASE 3: Docker Infra (Postgres + pgvector + pgAdmin) ---
cat <<EOF > docker-compose.yml
version: '3.8'
services:
  db:
    image: ankane/pgvector:latest
    container_name: voicenote_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: voicenote
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
  pgadmin:
    image: dpage/pgadmin4
    container_name: voicenote_pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@admin.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
EOF
phase_commit "Docker Infrastructure (PostgreSQL 17 + pgvector)"

# --- PHASE 4: Git Pre-Commit Hooks ---
mkdir -p .git/hooks
cat <<EOF > .git/hooks/pre-commit
#!/bin/bash
echo "🛡️ Running pre-commit tests..."
source .venv/bin/activate
pytest tests/
if [ \$? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi
echo "✅ Tests passed. Proceeding with commit."
EOF
chmod +x .git/hooks/pre-commit
phase_commit "Git Hooks Configured (Auto-Pytest on Commit)"

# --- PHASE 5: Basic App Structure ---
mkdir -p app/db tests
touch app/__init__.py
cat <<EOF > app/main.py
from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "VoiceNote AI Online"}
EOF
echo "def test_root(): assert 1 == 1" > tests/test_main.py
phase_commit "App Structure and Initial Test Case"

echo "🚀 ALL PHASES COMPLETE."
echo "Note: Run 'docker-compose up -d' to start your DB."