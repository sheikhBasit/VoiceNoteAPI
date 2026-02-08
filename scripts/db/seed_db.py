"""
Database Seeding Script
Populates VoiceNote database with sample data using Python ORM
Run: python scripts/seed_db.py
"""

import asyncio
import os
import sys
from datetime import datetime
import time
import uuid
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.db.models import User, Note, Task, UserRole, Priority, NoteStatus, CommunicationType

# Database URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/voicenote"
)

# Create engine and session
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables():
    """Create all database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database tables created successfully")


async def seed_users(session: AsyncSession):
    """Seed admin and test users"""
    current_time = int(time.time() * 1000)
    
    # Admin Users
    admin_users = [
        User(
            id="admin_user_001",
            name="System Admin",
            email="admin@voicenote.app",
            authorized_devices=[{
                "device_id": "admin_device_001",
                "device_model": "Server",
                "authorized_at": current_time
            }],
            current_device_id="admin_device_001",
            last_login=current_time,
            is_deleted=False,
            is_admin=True,
            admin_created_at=current_time,
            admin_permissions={
                "can_view_all_users": True,
                "can_delete_users": True,
                "can_view_all_notes": True,
                "can_delete_notes": True,
                "can_manage_admins": True,
                "can_view_analytics": True,
                "can_modify_system_settings": True,
                "can_moderate_content": True,
                "can_manage_roles": True,
                "can_export_data": True,
                "permission_level": "full",
                "granted_by": "system"
            }
        ),
        User(
            id="moderator_user_001",
            name="Content Moderator",
            email="moderator@voicenote.app",
            authorized_devices=[{
                "device_id": "moderator_device_001",
                "device_model": "Server",
                "authorized_at": current_time
            }],
            current_device_id="moderator_device_001",
            last_login=current_time,
            is_deleted=False,
            is_admin=True,
            admin_created_at=current_time,
            admin_permissions={
                "can_moderate_content": True,
                "can_view_all_notes": True,
                "can_delete_notes": True,
                "permission_level": "moderator",
                "granted_by": "system"
            }
        ),
        User(
            id="viewer_user_001",
            name="Analytics Viewer",
            email="viewer@voicenote.app",
            authorized_devices=[{
                "device_id": "viewer_device_001",
                "device_model": "Server",
                "authorized_at": current_time
            }],
            current_device_id="viewer_device_001",
            last_login=current_time,
            is_deleted=False,
            is_admin=True,
            admin_created_at=current_time,
            admin_permissions={
                "can_view_all_users": True,
                "can_view_analytics": True,
                "can_view_all_notes": True,
                "permission_level": "viewer",
                "granted_by": "system"
            }
        ),
    ]
    
    # Test Users
    test_users = [
        User(
            id=f"test_user_{str(i).zfill(3)}",
            name=f"Test User {i}",
            email=f"test{i}@voicenote.app",
            authorized_devices=[{
                "device_id": f"device_{str(i).zfill(3)}",
                "device_model": ["iPhone", "Android", "iPad", "Windows"][i % 4],
                "authorized_at": current_time
            }],
            current_device_id=f"device_{str(i).zfill(3)}",
            last_login=current_time,
            is_deleted=False,
        )
        for i in range(1, 11)  # Create 10 test users
    ]
    
    all_users = admin_users + test_users
    
    from sqlalchemy import select
    for user in all_users:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == user.email))
        existing_user = result.scalars().first()
        if existing_user:
            print(f"⏩ User {user.email} already exists, skipping.")
            continue
        session.add(user)
    
    await session.commit()
    print(f"✅ Seeded {len(all_users)} users ({len(admin_users)} admin, {len(test_users)} test)")


async def seed_notes(session: AsyncSession):
    """Seed sample notes"""
    current_time = int(time.time() * 1000)
    
    # Get test users
    from sqlalchemy import select
    result = await session.execute(select(User).where(User.email.like('test%')))
    test_users = result.scalars().all()
    
    notes = []
    for idx, user in enumerate(test_users[:5]):  # Create notes for first 5 users
        for note_num in range(1, 3):  # 2 notes per user
            note = Note(
                id=f"note_{user.id}_{str(note_num).zfill(3)}",
                user_id=user.id,
                title=f"Meeting Notes - {note_num}",
                summary=f"Summary of meeting {note_num} for {user.name}",
                priority=Priority.HIGH if note_num == 1 else Priority.MEDIUM,
                transcript_groq=f"This is the transcribed text of note {note_num}",
                timestamp=current_time - (1000 * 60 * 60 * (3 - note_num)),  # Vary timestamps
                is_deleted=False,
            )
            notes.append(note)
    
    for note in notes:
        # Check if note already exists
        result = await session.execute(select(Note).where(Note.id == note.id))
        if result.scalars().first():
            print(f"⏩ Note {note.id} already exists, skipping.")
            continue
        session.add(note)
    
    await session.commit()
    print(f"✅ Seeded {len(notes)} notes")


async def seed_tasks(session: AsyncSession):
    """Seed sample tasks"""
    current_time = int(time.time() * 1000)
    
    # Get notes with users
    from sqlalchemy import select
    result = await session.execute(select(Note).limit(10))
    notes = result.scalars().all()
    
    tasks = []
    for note in notes[:5]:
        for task_num in range(1, 3):  # 2 tasks per note
            task = Task(
                id=f"task_{note.id}_{str(task_num).zfill(3)}",
                note_id=note.id,
                user_id=note.user_id,
                description=f"Action item {task_num} from {note.title}",
                priority=Priority.HIGH if task_num == 1 else Priority.MEDIUM,
                is_done=task_num != 1,
                deadline=current_time + (1000 * 60 * 60 * 24 * (7 + task_num)),  # Next week
                assigned_entities=[{"name": f"Person {task_num}"}],
                communication_type=CommunicationType.WHATSAPP if task_num % 2 == 0 else CommunicationType.SMS,
                created_at=current_time,
                is_deleted=False,
            )
            tasks.append(task)
    
    for task in tasks:
        # Check if task already exists
        result = await session.execute(select(Task).where(Task.id == task.id))
        if result.scalars().first():
            print(f"⏩ Task {task.id} already exists, skipping.")
            continue
        session.add(task)
    
    await session.commit()
    print(f"✅ Seeded {len(tasks)} tasks")


async def verify_seeding(session: AsyncSession):
    """Verify seeding was successful"""
    from sqlalchemy import select, func
    
    # Count users
    user_count = await session.scalar(select(func.count(User.id)))
    admin_count = await session.scalar(
        select(func.count(User.id)).where(User.is_admin == True)
    )
    
    # Count notes
    note_count = await session.scalar(select(func.count(Note.id)))
    
    # Count tasks
    task_count = await session.scalar(select(func.count(Task.id)))
    
    print("\n" + "="*50)
    print("📊 SEEDING VERIFICATION")
    print("="*50)
    print(f"✅ Total Users: {user_count}")
    print(f"✅ Admin Users: {admin_count}")
    print(f"✅ Regular Users: {user_count - admin_count}")
    print(f"✅ Total Notes: {note_count}")
    print(f"✅ Total Tasks: {task_count}")
    print("="*50)


async def main():
    """Main seeding function"""
    print("\n" + "="*50)
    print("🌱 VOICENOTE DATABASE SEEDING")
    print("="*50)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create tables if they don't exist
            await create_tables()
            
            # Seed data
            await seed_users(session)
            await seed_notes(session)
            await seed_tasks(session)
            
            # Verify
            await verify_seeding(session)
            
            print("\n✅ Database seeding completed successfully!")
            print("="*50 + "\n")
            
        except Exception as e:
            print(f"\n❌ Error during seeding: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
