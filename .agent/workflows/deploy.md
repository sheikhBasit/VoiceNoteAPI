---
description: How to deploy the VoiceNote API using Docker Compose
---
1. Rent a VPS (DigitalOcean, AWS, etc.)
2. SSH into your VPS
3. Install Docker:
   ```bash
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   ```
4. Clone your repository:
   ```bash
   git clone <your-repo-url>
   cd VoiceNoteAPI
   ```
5. Create .env file:
   ```bash
   cp .env.example .env
   # Edit with production keys
   nano .env
   ```
6. Run Docker Compose:
   ```bash
   docker compose up --build -d
   ```
7. View logs (optional):
   ```bash
   docker compose logs -f
   ```
