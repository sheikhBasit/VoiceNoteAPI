
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, "/mnt/muaaz/VoiceNoteAPI")

from app.db import models
from app.services.task_service import TaskService

def verify_task_deduplication():
    # Use the running PG DB
    db_url = "postgresql://postgres:password@localhost:5433/voicenote"
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        user_id = "test_user_dedup"
        # Ensure user exists
        user = db.query(models.User).filter_by(id=user_id).first()
        if not user:
            user = models.User(id=user_id, email="dedup@test.com", name="Dedup User")
            db.add(user)
            db.commit()
            
        note_id = "test_note_id"
        note = db.query(models.Note).filter_by(id=note_id).first()
        if not note:
            note = models.Note(id=note_id, user_id=user_id, title="Test Note", transcript_groq="Test contents", summary="Summary")
            db.add(note)
            db.commit()
            
        service = TaskService(db)
        
        title = "Unique Task Title"
        note_id = "test_note_id"
        
        # 1. Create task
        print(f"Creating task first time...")
        t1 = service.create_task_with_deduplication(
            user_id=user_id,
            title=title,
            description="First attempt",
            note_id=note_id
        )
        print(f"Task 1 ID: {t1.id}")
        
        # 2. Try to create again with same title/note
        print(f"Creating task second time (should return same ID)...")
        t2 = service.create_task_with_deduplication(
            user_id=user_id,
            title=title,
            description="Second attempt (different description)",
            note_id=note_id
        )
        print(f"Task 2 ID: {t2.id}")
        
        if t1.id == t2.id:
            print("\n✅ Task Deduplication (Ghost Task Prevention) VERIFIED!")
        else:
            print("\n❌ Task Deduplication FAILED! Two separate tasks were created.")
            
        # Cleanup
        db.delete(t1)
        db.commit()
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_task_deduplication()
