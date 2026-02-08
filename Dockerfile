# Build stage
FROM python:3.11-slim as builder

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies for audio processing and PG connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libpq-dev \
    gcc \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies using CPU-only wheels for ML libs to save ~3GB
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    # First install CORE ml libs from CPU index
    pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu && \
    # Then install the rest, but force CPU index as extra to prevent overrides
    pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu && \
    # Explicitly clear out any nvidia/triton packages that might have been pulled as transitive deps
    pip list | grep nvidia | awk '{print $1}' | xargs pip uninstall -y || true && \
    pip uninstall -y triton || true && \
    find /usr/local/lib/python3.11/site-packages -name "__pycache__" -type d -exec rm -rf {} +

# Pre-download AI embedding model to avoid startup delays
RUN python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    echo "AI model pre-downloaded successfully"

# Runtime stage
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libpq5 \
    curl \
    wget \
    postgresql-client \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-downloaded AI model cache from builder
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

# Copy application code
COPY . .

# Clean up any Python bytecode cache that might have been copied
# This prevents old migration .pyc files from causing issues
RUN find /app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /app -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /app -type f -name "*.pyo" -delete 2>/dev/null || true && \
    echo "Python cache cleaned"

# Create necessary directories
RUN mkdir -p uploads scripts logs && \
    chmod 777 uploads logs && \
    chmod +x scripts/*.py scripts/*.sh 2>/dev/null || true

# Add a healthcheck script
COPY <<EOF /app/healthcheck.py
import requests
import sys
try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    sys.exit(0 if response.status_code == 200 else 1)
except Exception as e:
    print(f"Health check failed: {e}")
    sys.exit(1)
EOF

# Expose ports
EXPOSE 8000

# Default command - can be overridden by docker-compose
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]