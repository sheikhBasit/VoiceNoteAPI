"""
Database Initialization Script

Initializes PostgreSQL database with all required tables and schemas.
Also creates the SQLite test database for running tests.

Usage:
    python scripts/init_db.py --env production    # Init PostgreSQL
    python scripts/init_db.py --env test          # Init SQLite for tests
    python scripts/init_db.py --seed              # Also run seed data
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.db.models import Base
from app.db.session import get_database_url
from app.core.config import settings

def init_database(database_url: str, drop_existing: bool = False):
    """Initialize database with all tables"""
    print(f"🗄️  Initializing database: {database_url}")
    
    try:
        engine = create_engine(database_url, echo=False)
        
        if drop_existing:
            print("🗑️  Dropping existing tables...")
            Base.metadata.drop_all(engine)
            print("✅ Tables dropped")
        
        print("📋 Creating tables...")
        Base.metadata.create_all(engine)
        print("✅ Tables created successfully")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = result.fetchall()
            
        print(f"\n✨ Created {len(tables)} tables:")
        for table in tables:
            print(f"   • {table[0]}")
        
        return engine
        
    except SQLAlchemyError as e:
        print(f"❌ Database error: {e}")
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

def init_test_database():
    """Initialize SQLite database for testing"""
    print("\n🧪 Setting up test database (SQLite)...")
    
    test_db_path = Path(__file__).parent.parent.parent / "test.db"
    
    if test_db_path.exists():
        print(f"🗑️  Removing existing test database: {test_db_path}")
        test_db_path.unlink()
    
    database_url = f"sqlite:///{test_db_path}"
    init_database(database_url)
    
    print(f"✅ Test database ready: {test_db_path}")

def init_production_database():
    """Initialize production PostgreSQL database"""
    print("\n🏢 Setting up production database (PostgreSQL)...")
    
    database_url = get_database_url()
    
    if not database_url.startswith("postgresql"):
        print("⚠️  Warning: Not using PostgreSQL in production!")
    
    init_database(database_url, drop_existing=False)
    print("✅ Production database ready")

def print_summary():
    """Print summary information"""
    print("\n" + "="*70)
    print("📊 DATABASE INITIALIZATION SUMMARY")
    print("="*70)
    print(f"Database URL: {get_database_url()}")
    print(f"Database Name: {settings.DATABASE_NAME}")
    print(f"Database User: {settings.DATABASE_USER}")
    print(f"Database Host: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")
    print("="*70)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Initialize VoiceNote databases")
    parser.add_argument(
        "--env",
        choices=["production", "test", "both"],
        default="both",
        help="Which environment to initialize"
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating new ones"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Also run seed data after initialization"
    )
    
    args = parser.parse_args()
    
    print("🚀 VoiceNote Database Initialization\n")
    
    try:
        if args.env in ["test", "both"]:
            init_test_database()
        
        if args.env in ["production", "both"]:
            init_production_database()
        
        print_summary()
        
        if args.seed:
            print("\n🌱 Running seed data...")
            from scripts.db.seed_data import main as seed_main
            seed_main()
        
        print("\n✨ Initialization complete!")
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
