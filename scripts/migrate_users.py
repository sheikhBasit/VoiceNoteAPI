from app.db.session import SessionLocal, sync_engine as engine
from sqlalchemy import text

def run_migration():
    print("🔄 Starting User Schema Migration...")
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        try:
            # 1. Add new columns
            print("Adding 'authorized_devices' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS authorized_devices JSONB DEFAULT '[]'"))
            
            print("Adding 'current_device_id' column...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS current_device_id VARCHAR"))
            
            # 2. Migrate data (Optional: move old device_id to authorized_devices if needed)
            # For now, we will just wipe old columns as this is a breaking change requested by user
            
            # 3. Drop old columns
            print("Dropping old columns (token, device_id, device_model)...")
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS token"))
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS device_id"))
            conn.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS device_model"))
            
            print("✅ Migration Complete!")
            
        except Exception as e:
            print(f"❌ Migration Failed: {e}")

if __name__ == "__main__":
    run_migration()
