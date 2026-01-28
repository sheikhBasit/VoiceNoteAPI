# Deployment Guide for VoiceNote API

## Understanding Your Architecture

Your application is a **Full-Stack AI System** with multiple moving parts:

1.  **FastAPI Server (`api`)**: Handles HTTP requests.
2.  **Celery Worker (`celery_worker`)**: Processes AI tasks (transcription, embeddings, Q&A) in the background.
3.  **Celery Beat (`celery_beat`)**: Triggers scheduled tasks (e.g., weekly reports).
4.  **PostgreSQL (`db`)**: Stores data + Vectors (pgvector).
5.  **Redis (`redis`)**: Message broker for Celery and caching.

---

## 🛑 Why Vercel Is Not Enough

**Vercel is a "Serverless" platform.** It is designed for apps that sleep until they get a request and then wake up for a few seconds.

-   ✅ **Good for**: The `api` service (FastAPI).
-   ❌ **Bad for**: The `celery_worker`. Vercel shuts down processes immediately after a request finishes. **Your background AI tasks will be killed instantly on Vercel.**
-   ❌ **Bad for**: `db` and `redis`. Vercel does not host databases.

**Recommendation**: Since you want to "run all the services", **Docker** is the correct solution. It runs everything together in sync.

---

## 🚀 Option 1: Docker Deployment (Recommended)

This method runs ALL your services (`api`, `worker`, `db`, `redis`, etc.) on a single Virtual Private Server (VPS).

### Prerequisites
1.  **Rent a VPS**: DigitalOcean (Droplet), AWS (EC2), Hetzner, or Linode.
    -   *Recommended Specs*: 4GB+ RAM (AI models like local embeddings need RAM), 2 vCPUs.
2.  **Install Docker**: Run the following on your server:
    ```bash
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    ```

### Deployment Steps

1.  **Copy Your Code**: Upload your project to the server (via Git).
    ```bash
    git clone https://github.com/your-username/VoiceNoteAPI.git
    cd VoiceNoteAPI
    ```

2.  **Configure Environment**:
    Create a `.env` file with **production** values or rename the existing one.
    ```bash
    cp .env.example .env
    # Edit keys (OpenAI, Deepgram, Stripe, etc.)
    nano .env
    ```
    *Important*: Ensure `DATABASE_URL` uses the docker service name `db`, e.g., `postgresql+asyncpg://postgres:password@db:5432/voicenote`.

3.  **Run with Docker Compose**:
    This single command builds your images and starts all services (Database, API, Workers, Redis, Monitoring).
    ```bash
    docker compose up --build -d
    ```

4.  **Verify**:
    -   API: `http://<your-server-ip>:8000/docs`
    -   Monitoring (Grafana): `http://<your-server-ip>:3002`

---

## 🦎 Option 2: Deploy with Komodo (UI Manager)

If you are using **Komodo** (by mbecker) to manage your server, deployment is even easier.

1.  **Add Repository**:
    -   Go to **Stacks** > **Create Stack**.
    -   Name: `voicenote-api`.
    -   **Deployment Strategy**: Select **Git Repository**.
    -   **Repo URL**: Your GitHub URL (e.g., `https://github.com/yourname/VoiceNoteAPI`).
    -   **Branch**: `main` (or your active branch).

2.  **Environment Variables**:
    -   Copy the content of your local `.env` file.
    -   Paste it into the **Environment Variables** section in Komodo.

3.  **Build & Deploy**:
    -   Click **Deploy**.
    -   Komodo will clone the repo, run `docker compose up --build`, and manage the health of your containers.
    -   You can view logs and restart services directly from the Komodo UI.

---

## ☁️ Option 3: Hybrid (Advanced)

If you *really* want to use Vercel for the API, you must split your stack:

1.  **API**: Deployed on **Vercel** (using the `vercel.json` I created).
2.  **Database**: Hosted on **Supabase** or **Neon**.
3.  **Redis**: Hosted on **Upstash**.
4.  **Workers**: Deployed on **Railway** or **Render** (because Vercel cannot run them).

**This is complex/expensive** because you manage 4 different providers. Stick to Option 1 for now.
