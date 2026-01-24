#!/usr/bin/env python3
"""
Generate MOCK embeddings for all seeded notes.
This avoids downloading heavy AI models during testing.
"""
import sys
import os
import random
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.db import models
import asyncio

async def generate_mock_embeddings():
    db = SessionLocal()
    
    try:
        notes = db.query(models.Note).filter(
            models.Note.is_deleted == False
        ).all()
        
        print(f"Found {len(notes)} notes. generating MOCK embeddings...")
        
        updated_count = 0
        
        for i, note in enumerate(notes, 1):
            if note.embedding is not None:
                continue
                
            # Generate random 384-dimensional vector (standard for all-MiniLM-L6-v2)
            mock_embedding = [random.uniform(-1.0, 1.0) for _ in range(384)]
            
            note.embedding = mock_embedding
            updated_count += 1
            
            if i % 10 == 0:
                db.commit()
                print(f"[{i}/{len(notes)}] Processed...")
                
        db.commit()
        print(f"\n✅ Mock Embedding generation complete! Updated {updated_count} notes.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(generate_mock_embeddings())
