from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.db import models
from app.schemas import note_schema
from app.worker.tasks import process_audio_pipeline  # Your Celery task
import time
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0")

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])

@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def process_note(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    instruction: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """POST /process: Main Upload for audio processing."""
    note_id = str(uuid.uuid4())
    # Save the file temporarily
    temp_path = f"uploads/{note_id}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    # Trigger Celery pipeline
    process_audio_pipeline.delay(note_id, temp_path, user_id, instruction)
    
    return {"note_id": note_id, "message": "Processing started in background"}

@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(user_id: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """GET /: Returns all non-deleted notes for the user (paginated)."""
    return db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).offset(skip).limit(limit).all()

@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(note_id: str, db: Session = Depends(get_db)):
    """GET /{note_id}: Returns full note detail."""
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@router.patch("/{note_id}")
def update_note_status(note_id: str, update_data: note_schema.NoteUpdate, db: Session = Depends(get_db)):
    """PATCH /{note_id}: Update Pin, Archive, or Like."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(db_note, key, value)
    
    db.commit()
    return {"message": "Update successful"}

@router.delete("/{note_id}")
def soft_delete_note(note_id: str, db: Session = Depends(get_db)):
    """DELETE /{note_id}: Soft Delete logic."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db_note.is_deleted = True
    db_note.deleted_at = int(time.time() * 1000)
    db.commit()
    return {"message": "Note deleted successfully"}

@router.post("/{note_id}/ask")
@limiter.limit("5/minute")
def ask_ai_assistant(note_id: str, question: str, db: Session = Depends(get_db)):
    """POST /{note_id}/ask: AI Assistant interaction."""
    # Logic to fetch note context and send to LLM goes here
    return {"answer": "This is a placeholder for the AI assistant response."}