#!/usr/bin/env python3
"""Generate embeddings for all seeded notes"""
import sys
import os
import time
from dotenv import load_dotenv

# Load env before imports that might use env vars
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import SessionLocal
from app.db import models
from app.services.ai_service import AIService
import asyncio

async def generate_embeddings():
    db = SessionLocal()
    ai_service = AIService()
    
    try:
        # Get all notes, not just ones without embeddings, to ensure complete coverage for search tests
        # But prioritize those without embeddings
        notes = db.query(models.Note).filter(
            models.Note.is_deleted == False
        ).all()
        
        print(f"Found {len(notes)} notes total. Checking embeddings...")
        
        updated_count = 0
        skipped_count = 0
        
        for i, note in enumerate(notes, 1):
            try:
                if note.embedding is not None:
                    skipped_count += 1
                    continue

                # Create embedding from transcript or summary
                content = note.title + "\n" + (note.summary or "") + "\n" + (note.transcript_deepgram or note.transcript_groq or note.transcript_android or "")
                
                if content.strip():
                    # Add small delay to avoid rate limits
                    await asyncio.sleep(0.5) 
                    
                    embedding = await ai_service.generate_embedding(content[:8000]) # Truncate if too long
                    note.embedding = embedding
                    db.commit()
                    updated_count += 1
                    print(f"[{i}/{len(notes)}] Generated embedding for: {note.title[:50]} ({updated_count} new)")
                else:
                    print(f"[{i}/{len(notes)}] Skipped (no content): {note.id}")
            except Exception as e:
                print(f"[{i}/{len(notes)}] Error for {note.id}: {e}")
                db.rollback()
                # Wait longer on error in case of rate limit
                await asyncio.sleep(2)
        
        print(f"\n✅ Embedding generation complete! Updated {updated_count}, Skipped {skipped_count} existing.")
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(generate_embeddings())
