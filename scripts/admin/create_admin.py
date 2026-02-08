import sys
import os
import time

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import models
from app.services.auth_service import get_password_hash
import uuid

# Fix for sync environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/voicenote")
SYNC_DATABASE_URL = DATABASE_URL.replace("asyncpg", "psycopg2") if "asyncpg" in DATABASE_URL else DATABASE_URL
if "postgresql://" in SYNC_DATABASE_URL and "psycopg2" not in SYNC_DATABASE_URL:
    SYNC_DATABASE_URL = SYNC_DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

engine = create_engine(SYNC_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_admin(email, password, name="Admin User"):
    db = SessionLocal()
    try:
        # Check if user already exists
        user = db.query(models.User).filter(models.User.email == email).first()
        if user:
            print(f"User {email} already exists. Promoting to admin...")
            user.is_admin = True
            user.password_hash = get_password_hash(password)
        else:
            print(f"Creating new admin user {email}...")
            user = models.User(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                is_admin=True,
                password_hash=get_password_hash(password),
                authorized_devices=[{
                    "device_id": "admin-web",
                    "device_model": "Web Dashboard",
                    "biometric_token": "admin-token",
                    "authorized_at": int(time.time())
                }],
                current_device_id="admin-web"
            )
            db.add(user)
        
        db.commit()
        print("Successfully created/updated admin user!")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/create_admin.py <email> <password>")
    else:
        create_admin(sys.argv[1], sys.argv[2])
