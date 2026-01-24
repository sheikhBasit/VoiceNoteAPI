from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.db import models
from app.schemas import note as note_schema
from app.schemas.note import NoteSemanticAnalysis
from app.worker.task import process_voice_note_pipeline  # Celery task
import time
import uuid
import os
import asyncio

from slowapi import Limiter
from slowapi.util import get_remote_address
from app.utils.json_logger import JLogger
from app.services.ai_service import AIService
from app.services.search_service import SearchService
from app.services.analytics_service import AnalyticsService
from app.utils.security import verify_device_signature, verify_note_ownership
from app.services.deletion_service import DeletionService
from app.services.auth_service import get_current_user

ai_service = AIService()
search_service = SearchService(ai_service)
analytics_service = AnalyticsService()
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0"))

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])

@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def process_note(
    request: Request,
    file: UploadFile = File(...),
    mode: Optional[str] = Form("GENERIC"), # New: Cricket/Quranic Mode
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature) # Security requirement
):
    """POST /process: Main Upload for audio processing with validation and security."""
    # ✅ VALIDATION: File type check
    ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac"}
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in ALLOWED_EXTENSIONS:
        JLogger.warning("Unsupported file type upload attempt", 
                        filename=file.filename, 
                        extension=file_ext, 
                        user_id=current_user.id)
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # ✅ VALIDATION: File size check (50MB limit) via stream
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    note_id = str(uuid.uuid4())
    JLogger.info("Starting voice note upload", 
                 note_id=note_id, 
                 user_id=current_user.id, 
                 filename=file.filename)
    
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        
    temp_path = f"uploads/{note_id}_{file.filename}"
    total_size = 0
    
    with open(temp_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # Read in 1MB chunks
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                os.remove(temp_path)
                JLogger.warning("File upload too large", 
                                user_id=current_user.id, 
                                size_bytes=total_size)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: 50MB."
                )
            buffer.write(chunk)

    # Trigger Celery pipeline with mode support
    user_role = current_user.primary_role.name if current_user.primary_role else "GENERIC"
    if mode and mode != "GENERIC":
        user_role = f"{user_role}_{mode}"

    process_voice_note_pipeline.delay(note_id, temp_path, user_role)
    
    return {"note_id": note_id, "message": f"Processing started in {mode} mode"}

@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(
    request: Request,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=500, description="Max 500 items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /: Returns all non-deleted notes for the user (paginated)."""
    return db.query(models.Note).filter(
        models.Note.user_id == current_user.id,
        models.Note.is_deleted == False
    ).offset(skip).limit(limit).all()

@router.get("/dashboard", response_model=note_schema.DashboardResponse)
def get_dashboard_metrics(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    GET /dashboard: Provides the "Productivity Pulse" analytics.
    Exposes Topic Heatmap, Task Velocity, and Meeting ROI.
    """
    try:
        return analytics_service.get_productivity_pulse(db, current_user.id)
    except Exception as e:
        JLogger.error("Dashboard analytics pulse failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error: Analytics pulse failed to load"
        )

@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(note_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """GET /{note_id}: Returns full note detail (ownership validated)."""
    return verify_note_ownership(db, current_user.id, note_id)

@router.patch("/{note_id}", response_model=note_schema.NoteResponse)
async def update_note(
    note_id: str, 
    update_data: note_schema.NoteUpdate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    PATCH /{note_id}: Unified update for note details.
    Handles title, summary, priority, status, and soft deletion/restore.
    """
    db_note = verify_note_ownership(db, current_user.id, note_id)
    
    data = update_data.model_dump(exclude_unset=True)

    # Handle soft deletion/restore
    if "is_deleted" in data:
        if data["is_deleted"]:
            # Standard logic: Check for high priority tasks
            high_priority_active_tasks = db.query(models.Task).filter(
                models.Task.note_id == note_id,
                models.Task.priority == models.Priority.HIGH,
                models.Task.is_done == False,
                models.Task.is_deleted == False
            ).first()
            if high_priority_active_tasks:
                raise HTTPException(status_code=400, detail="Cannot delete note: It contains in-progress HIGH priority tasks.")
            
            DeletionService.soft_delete_note(db, note_id, deleted_by=current_user.id)
            db.refresh(db_note)
            return db_note
        else:
            DeletionService.restore_note(db, note_id, restored_by=current_user.id)
            db.refresh(db_note)
            return db_note

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
        if key == "is_deleted": continue
        setattr(db_note, key, value)
    
    db_note.updated_at = int(time.time() * 1000)
    db.commit()
    return db_note


@router.delete("/{note_id}")
def delete_note(
    note_id: str, 
    hard: bool = False, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    DELETE /{note_id}: Professional deletion handling via DeletionService.
    Includes redundancy check: Block deletion if note has in-progress HIGH priority tasks.
    """
    verify_note_ownership(db, current_user.id, note_id)
    # REDUNDANCY CHECK: Block deletion if note has in-progress HIGH priority tasks
    high_priority_active_tasks = db.query(models.Task).filter(
        models.Task.note_id == note_id,
        models.Task.priority == models.Priority.HIGH,
        models.Task.is_done == False,
        models.Task.is_deleted == False
    ).first()
    
    if high_priority_active_tasks:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete note: It contains in-progress HIGH priority tasks."
        )
    
    result = DeletionService.soft_delete_note(db, note_id, deleted_by=current_user.id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.post("/{note_id}/ask")
@limiter.limit("5/minute")
async def ask_ai(
    request: Request,
    note_id: str, 
    question: str = Body(..., embed=True), 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """POST /{note_id}/ask: Query AI about a note's content with error handling."""
    # Verify ownership and deletion status before processing
    db_note = verify_note_ownership(db, current_user.id, note_id)
    
    if db_note.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: This voice note has been deleted and must be restored before use"
        )
    
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
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timeout: The AI service took too long to respond. Please try again"
        )
    except Exception as e:
        JLogger.error("AI question-answer failed", note_id=note_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: AI failed to process your request"
        )


@router.post("/search")
@limiter.limit("10/minute")
async def search_notes_hybrid(
    request: Request,
    query: note_schema.SearchQuery,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    POST /search: Unified V-RAG (Voice-Retrieval Augmented Generation).
    Searches local notes first using pgvector, falls back to Web (Tavily) if needed.
    """
    try:
        result = await search_service.unified_rag_search(db, current_user.id, query.query)
        return result
    except Exception as e:
        # Use current_user.id if available, otherwise just log error
        user_id = getattr(current_user, 'id', 'system') if 'current_user' in locals() else 'unknown'
        JLogger.error("System error in note API", user_id=user_id, error=str(e), path=request.url.path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error: Operation failed to process"
        )


@router.get("/{note_id}/whatsapp")
def get_whatsapp_draft(note_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """
    GET /{note_id}/whatsapp: Generates a WhatsApp deep-link for the note's summary.
    Requirement: "Voice-to-WhatsApp Draft"
    """
    note = verify_note_ownership(db, current_user.id, note_id)
    
    text = f"VoiceNote Note: {note.title}\n\nSummary: {note.summary}\n\nTasks:\n"
    tasks = db.query(models.Task).filter(models.Task.note_id == note_id).all()
    for t in tasks:
        status_icon = "✅" if t.is_done else "⏳"
        text += f"- {status_icon} {t.description}\n"
    
    import urllib.parse
    encoded_text = urllib.parse.quote(text)
    wa_link = f"https://wa.me/?text={encoded_text}"
    
    return {"whatsapp_link": wa_link, "draft": text}

@router.post("/{note_id}/semantic-analysis", response_model=NoteSemanticAnalysis)
async def analyze_note_semantics(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    POST /{note_id}/semantic-analysis: Deep dive into note meaning.
    Provides sentiment, emotional tone, hidden patterns, and suggested questions.
    """
    db_note = verify_note_ownership(db, current_user.id, note_id)
    
    if db_note.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Permission denied: This voice note has been deleted and must be restored before analysis"
        )
    
    transcript = db_note.transcript_deepgram or db_note.transcript_groq or db_note.transcript_android
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Validation failed: Note has no transcript to analyze"
        )
    
    try:
        analysis = await asyncio.wait_for(
            ai_service.semantic_analysis(
                transcript=transcript, 
                user_role=db_note.user.primary_role.value if db_note.user else "GENERIC"
            ),
            timeout=45.0
        )
        return analysis
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timeout: Semantic analysis took too long. Please try again"
        )
    except Exception as e:
        JLogger.error("Semantic analysis failed", note_id=note_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Semantic analysis failed"
        )


    