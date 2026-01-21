from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
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
from app.services.ai_service import AIService
ai_service = AIService()
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
    """POST /process: Main Upload for audio processing with validation."""
    # ✅ VALIDATION: File type check
    ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac"}
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # ✅ VALIDATION: File size check (50MB limit)
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    file_content = await file.read()
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: 50MB. Got: {len(file_content) / 1024 / 1024:.2f}MB"
        )
    
    # ✅ VALIDATION: User exists
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    note_id = str(uuid.uuid4())
    # Save the file temporarily
    temp_path = f"uploads/{note_id}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(file_content)

    # Trigger Celery pipeline
    process_audio_pipeline.delay(note_id, temp_path, user_id, instruction)
    
    return {"note_id": note_id, "message": "Processing started in background"}

@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(
    user_id: str, 
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=500, description="Max 500 items per page"),
    db: Session = Depends(get_db)
):
    """GET /: Returns all non-deleted notes for the user (paginated)."""
    return db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).offset(skip).limit(limit).all()

@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(note_id: str, user_id: str, db: Session = Depends(get_db)):
    """GET /{note_id}: Returns full note detail (ownership validated)."""
    note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id
    ).first()
    if not note:
        raise HTTPException(status_code=403, detail="Access denied or note not found")
    return note

@router.patch("/{note_id}")
async def update_note(
    note_id: str, 
    user_id: str,
    update_data: note_schema.NoteUpdate, 
    db: Session = Depends(get_db)
):
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id
    ).first()
    if not db_note:
        raise HTTPException(status_code=403, detail="Access denied or note not found")
    
    data = update_data.model_dump(exclude_unset=True)

    # Logic: Prevent archiving if Note has HIGH priority tasks that are not DONE
    if data.get("is_archived") is True and not db_note.is_archived:
        high_priority_tasks = db.query(models.Task).filter(
            models.Task.note_id == note_id,
            models.Task.priority == models.Priority.HIGH,
            models.Task.is_done == False,
            models.Task.is_deleted == False
        ).first()
        
        if high_priority_tasks:
            raise HTTPException(
                status_code=400, 
                detail="Cannot archive note: It contains unfinished HIGH priority tasks."
            )

    for key, value in data.items():
        setattr(db_note, key, value)
    
    # ✅ ADD TIMESTAMP ON UPDATE
    db_note.updated_at = int(time.time() * 1000)
    
    db.commit()
    return note_schema.NoteResponse.model_validate(db_note)


@router.delete("/{note_id}")
def delete_note(
    note_id: str, 
    user_id: str,
    hard: bool = False, 
    db: Session = Depends(get_db)
):
    """DELETE /{note_id}: Soft or Hard delete a note and all its associated tasks.
    
    Args:
        note_id: Note to delete
        user_id: Current user (for ownership validation)
        hard: If False, soft delete. If True, hard delete.
    """
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id
    ).first()
    if not db_note:
        raise HTTPException(status_code=403, detail="Access denied or note not found")
    
    # Cascade to Tasks
    tasks = db.query(models.Task).filter(models.Task.note_id == note_id).all()
    
    if hard:
        # Hard Delete Note & Tasks
        for task in tasks:
            db.delete(task)
        db.delete(db_note)
        msg = "Note and all related tasks permanently deleted."
    else:
        # Soft Delete Note & Tasks
        now = int(time.time() * 1000)
        db_note.is_deleted = True
        db_note.deleted_at = now
        for task in tasks:
            task.is_deleted = True
            task.deleted_at = now
        msg = "Note and tasks archived (Soft Delete)."
    
    db.commit()
    return note_schema.NoteResponse.model_validate(db_note)

@router.post("/{note_id}/ask")
@limiter.limit("5/minute")
async def ask_ai(
    note_id: str, 
    question: str, 
    user_id: str, 
    db: Session = Depends(get_db)
):
    """POST /{note_id}/ask: Query AI about a note's content with error handling."""
    # Verify ownership and deletion status before processing
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=403, detail="Access denied or note not found")
    
    # ✅ VALIDATION: Transcript exists
    transcript = db_note.transcript_deepgram or db_note.transcript_groq or db_note.transcript_android
    if not transcript:
        raise HTTPException(
            status_code=400, 
            detail="Note has no transcript. Transcription may still be processing."
        )
    
    try:
        # ✅ ERROR HANDLING: Try-except with timeout
        answer = await asyncio.wait_for(
            ai_service.llm_brain(
                transcript=transcript, 
                user_role=db_note.user.primary_role.value if db_note.user else "GENERIC",
                user_instruction=question
            ),
            timeout=30.0
        )
        return {"answer": answer.summary if hasattr(answer, 'summary') else str(answer)}
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI service took too long. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI processing failed: {str(e)}"
        )

@router.patch("/{note_id}/restore")
def restore_note(note_id: str, user_id: str, db: Session = Depends(get_db)):
    """PATCH /{note_id}/restore: Restore a soft-deleted note and all its associated tasks."""
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id
    ).first()
    if not db_note:
        raise HTTPException(status_code=403, detail="Access denied or note not found")
    
    # 1. Restore the Note
    db_note.is_deleted = False
    db_note.deleted_at = None
    db_note.updated_at = int(time.time() * 1000)
    
    # 2. Restore all Tasks associated with this note
    db.query(models.Task).filter(models.Task.note_id == note_id).update({
        "is_deleted": False, 
        "deleted_at": None
    })
    
    db.commit()
    return note_schema.NoteResponse.model_validate(db_note)

    