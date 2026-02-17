#!/bin/bash
# Quick Start Script for Admin API Testing
# This script starts the necessary services and creates an admin user

set -e

echo "========================================="
echo "Admin API Quick Start"
echo "========================================="
echo ""

# Check if docker-compose exists
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found"
    exit 1
fi

# Start Docker services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if services are running
if ! docker-compose ps | grep -q "postgres.*Up"; then
    echo "❌ PostgreSQL is not running"
    exit 1
fi

if ! docker-compose ps | grep -q "redis.*Up"; then
    echo "❌ Redis is not running"
    exit 1
fi

echo "✅ Services are running"
echo ""

# Run migrations
echo "🔄 Running database migrations..."
python3 -m alembic upgrade head || echo "⚠️  Migration warning (may be expected)"
echo ""

# Create admin user if it doesn't exist
echo "👤 Creating admin user..."
python3 << 'PYTHON_SCRIPT'
import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from app.db.models import User
from app.services.auth_service import hash_password

db = SessionLocal()

# Check if admin exists
admin = db.query(User).filter(User.email == "admin@example.com").first()

if not admin:
    admin = User(
        id="admin_user_001",
        email="admin@example.com",
        name="Admin User",
        password_hash=hash_password("adminpass123"),
        is_admin=True,
        admin_permissions={
            "can_view_analytics": True,
            "can_delete_tasks": True,
            "can_restore_tasks": True,
            "can_create_test_notes": True,
            "can_manage_api_keys": True,
            "can_manage_wallets": True,
        }
    )
    db.add(admin)
    db.commit()
    print("✅ Admin user created")
else:
    print("✅ Admin user already exists")

db.close()
PYTHON_SCRIPT

echo ""

# Start API server
echo "🚀 Starting API server..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start uvicorn
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
