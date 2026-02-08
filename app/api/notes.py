import os
import time
import traceback
import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, joinedload

from app.db import models
from app.db.session import get_db
from app.schemas import note as note_schema
from app.services.ai_service import AIService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import get_current_user
from app.services.deletion_service import DeletionService
from app.services.search_service import SearchService
from app.services.storage_service import StorageService
from app.utils.billing_utils import check_credit_balance, requires_tier
from app.utils.json_logger import JLogger
from app.utils.security import verify_device_signature, verify_note_ownership
from app.worker.task import analyze_note_semantics_task  # Celery tasks
from app.worker.task import generate_note_embeddings_task, note_process_pipeline

# Services are instantiated inside endpoints to avoid module-level hangs
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
)

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])


@router.get("/presigned-url")
async def get_presigned_url(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    GET /presigned-url: Generate a direct-to-storage upload link.
    Privacy-First: The audio bypasses the API server and goes straight to MinIO.
    """
    note_id = str(uuid.uuid4())
    storage_key = f"{current_user.id}/{note_id}.wav"

    storage_service = StorageService()
    try:
        upload_url = storage_service.generate_presigned_put_url(storage_key)
        return {
            "note_id": note_id,
            "storage_key": storage_key,
            "upload_url": upload_url,
            "expires_in": 3600,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate upload link. Storage service is unavailable.",
        )


@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def process_note(
    request: Request,
    file: Optional[UploadFile] = File(None),
    storage_key: Optional[str] = Form(None),  # New: Direct MinIO upload key
    note_id_override: Optional[str] = Form(None),  # New: For Pre-signed flow
    mode: Optional[str] = Form("GENERIC"),  # New: Cricket/Quranic Mode
    languages: Optional[str] = Form(None),  # New: Multilingual support (e.g. "en,ur")
    stt_model: Optional[str] = Form("nova"),  # New: nova, whisper, both
    document_uris: Optional[str] = Form(
        None
    ),  # Client-side document URIs (comma-separated)
    image_uris: Optional[str] = Form(None),  # Client-side image URIs (comma-separated)
    debug_sync: bool = Form(False),  # For local developer testing
    db: Session = Depends(get_db),
    current_user: models.User = Depends(requires_tier(models.SubscriptionTier.FREE)),
    _balance: bool = Depends(check_credit_balance(10)),  # Minimum cost to start process
    _sig: bool = Depends(verify_device_signature),  # Security requirement
):
    """POST /process: Main Upload for audio processing with validation and security."""

    # Define allowed file extensions
    ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a", "ogg", "flac"}

    if file and "." in file.filename:
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            JLogger.warning(
                "Unsupported file type upload attempt",
                filename=file.filename,
                extension=file_ext,
                user_id=current_user.id,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The uploaded file format is not supported. Please provide an audio file in one of the following formats: {', '.join(ALLOWED_EXTENSIONS)}.",
            )

    # ✅ STEP: Handle Note ID (Reuse if from Pre-signed URL flow)
    note_id = note_id_override if note_id_override else str(uuid.uuid4())
    temp_path = None

    # ✅ VALIDATION: File size check (50MB limit) via stream
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    if file:
        # Legacy File Upload Flow
        if not os.path.exists("uploads"):
            os.makedirs("uploads")

        file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else ""
        temp_path = f"uploads/{note_id}_{file.filename}"
        total_size = 0

        with open(temp_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    os.remove(temp_path)
                    raise HTTPException(status_code=413, detail="File too large")
                buffer.write(chunk)
    elif storage_key:
        # New Privacy-First Storage Key Flow
        # storage_key is already in MinIO
        pass
    else:
        raise HTTPException(
            status_code=400,
            detail="Missing audio sources. Provide 'file' or 'storage_key'.",
        )

    # Parse client-side URIs if provided
    doc_uri_list = (
        [d.strip() for d in document_uris.split(",")] if document_uris else []
    )
    img_uri_list = [i.strip() for i in image_uris.split(",")] if image_uris else []

    # Parse languages
    lang_list = (
        [l.strip() for l in languages.split(",")]
        if languages
        else current_user.preferred_languages
    )

    # ✅ STEP: Create initial record
    initial_note = models.Note(
        id=note_id,
        user_id=current_user.id,
        title=f"Processing: {file.filename if file else 'Storage Key Extraction'}",
        summary="AI is currently analyzing your audio...",
        status=models.NoteStatus.PENDING,
        raw_audio_url=storage_key if storage_key else temp_path,
        languages=lang_list,
        document_uris=doc_uri_list,  # Client-side URIs
        image_uris=img_uri_list,  # Client-side URIs
        stt_model=stt_model,
        timestamp=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
    )
    db.add(initial_note)
    db.commit()

    # Determine Queue (Simplified for now, could use file size or metadata)
    # Defaulting to 'short' unless we have a specific reason for 'long'
    target_queue = "short"

    # Trigger Celery pipeline
    if debug_sync:
        # Run the pipeline synchronously for immediate feedback in the API response
        result = note_process_pipeline(
            note_id,
            temp_path if temp_path else storage_key,
            mode,
            document_uris=doc_uri_list,
            image_uris=img_uri_list,
            languages=lang_list,
            stt_model=stt_model,
        )
        return {
            "note_id": note_id,
            "message": "Synchronous processing complete",
            "result": result,
        }

    note_process_pipeline.delay(
        note_id,
        temp_path if temp_path else storage_key,
        mode,
        document_uris=doc_uri_list,
        image_uris=img_uri_list,
        languages=lang_list,
        stt_model=stt_model,
    )

    return {"note_id": note_id, "message": f"Processing started in {mode} mode"}


@router.post(
    "/create",
    response_model=note_schema.NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    note_data: note_schema.NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not note_data.title or not note_data.title.strip():
        note_data.title = "Untitled Note"

    note_id = str(uuid.uuid4())
    db_note = models.Note(
        id=note_id,
        user_id=current_user.id,
        title=note_data.title,
        summary=note_data.summary or "",
        transcript_groq=note_data.transcript or "",
        priority=note_data.priority or models.Priority.MEDIUM,
        status=models.NoteStatus.DONE,
        timestamp=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
    )
    try:
        db.add(db_note)
        db.commit()
        db.refresh(db_note)

        # Trigger background tasks
        generate_note_embeddings_task.delay(note_id)
        if db_note.transcript_groq:
            analyze_note_semantics_task.delay(note_id)
    except Exception as e:
        db.rollback()
        JLogger.error(
            "Failed to create note in database", user_id=current_user.id, error=str(e)
        )
        if os.getenv("ENVIRONMENT") == "testing":
            traceback.print_exc()
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Failed to save note",
        )

    return db_note


@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(
    request: Request,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=500, description="Max 500 items per page"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /: Returns all non-deleted notes for the user (paginated)."""
    return (
        db.query(models.Note)
        .options(joinedload(models.Note.tasks))
        .filter(models.Note.user_id == current_user.id, models.Note.is_deleted == False)
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/dashboard", response_model=note_schema.DashboardResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    GET /dashboard: Provides the "Productivity Pulse" analytics.
    Exposes Topic Heatmap, Task Velocity, and Meeting ROI.
    """
    try:
        analytics_service = AnalyticsService()
        return analytics_service.get_productivity_pulse(db, current_user.id)
    except Exception as e:
        JLogger.error(
            "Dashboard analytics pulse failed", user_id=current_user.id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Analytics pulse failed to load",
        )


@router.get("/autocomplete", response_model=List[str])
def search_autocomplete(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    GET /autocomplete: Suggest note titles or tags.
    Fast prefix search for mobile search bar.
    """
    # 1. Search Titles
    titles = (
        db.query(models.Note.title)
        .filter(
            models.Note.user_id == current_user.id,
            models.Note.title.ilike(f"%{q}%"),
            models.Note.is_deleted == False,
        )
        .limit(5)
        .all()
    )

    # Flatten list of tuples
    suggestions = [t[0] for t in titles]

    return suggestions


@router.patch("/move")
def bulk_move_notes(
    note_ids: List[str] = Body(..., embed=True),
    folder_id: Optional[str] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    PATCH /move: Bulk move notes to a folder.
    pass folder_id=None to move to 'Uncategorized'.
    """
    # 1. Verify Folder (if provided)
    if folder_id:
        folder = (
            db.query(models.Folder)
            .filter(
                models.Folder.id == folder_id, models.Folder.user_id == current_user.id
            )
            .first()
        )
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

    # 2. Update Notes
    updated_count = (
        db.query(models.Note)
        .filter(models.Note.id.in_(note_ids), models.Note.user_id == current_user.id)
        .update({models.Note.folder_id: folder_id}, synchronize_session=False)
    )

    db.commit()

    return {"message": f"Moved {updated_count} notes successfully"}


@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    GET /{note_id}: Returns full note detail (ownership validated).
    Requirement: Add related_notes field using pgvector to find top 3 matches.
    Docstring: Avoids N+1 by fetching related notes in a single query after ownership check.
    """
    note = verify_note_ownership(db, current_user, note_id)

    # 🚀 Semantic Note Linking (Phase 3 Requirement)
    if note.embedding is not None:
        from app.db.models import Note

        # Use pgvector <-> (cosine distance) for the top 3 semantically closest notes
        related = (
            db.query(Note)
            .filter(
                Note.user_id == current_user.id,
                Note.id != note_id,
                Note.is_deleted == False,
            )
            .order_by(Note.embedding.cosine_distance(note.embedding))
            .limit(3)
            .all()
        )
        note.related_notes = related
    else:
        note.related_notes = []

    return note


@router.patch("/{note_id}", response_model=note_schema.NoteResponse)
async def update_note(
    note_id: str,
    update_data: note_schema.NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    PATCH /{note_id}: Unified update for note details.
    Handles title, summary, priority, status, and soft deletion/restore.
    """
    db_note = verify_note_ownership(db, current_user, note_id)

    # Block updates on deleted notes (unless it's a restore operation handled below)
    data = update_data.model_dump(exclude_unset=True)
    if db_note.is_deleted and "is_deleted" not in data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation restricted: This note is currently in the trash. Please restore it before making any further updates.",
        )

    # Handle soft deletion/restore
    if "is_deleted" in data:
        if data["is_deleted"]:
            # Standard logic: Check for high priority tasks
            high_priority_active_tasks = (
                db.query(models.Task)
                .filter(
                    models.Task.note_id == note_id,
                    models.Task.priority == models.Priority.HIGH,
                    models.Task.is_done == False,
                    models.Task.is_deleted == False,
                )
                .first()
            )
            if high_priority_active_tasks:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Action restricted: This note cannot be deleted while it contains incomplete high-priority tasks. Please complete or re-prioritize these tasks first.",
                )

            DeletionService.soft_delete_note(db, note_id, deleted_by=current_user.id)
            db.refresh(db_note)
            return db_note
        else:
            DeletionService.restore_note(db, note_id, restored_by=current_user.id)
            db.refresh(db_note)
            return db_note

    # Logic: Prevent archiving if Note has HIGH priority tasks that are not DONE
    if data.get("is_archived") is True and not db_note.is_archived:
        high_priority_tasks = (
            db.query(models.Task)
            .filter(
                models.Task.note_id == note_id,
                models.Task.priority == models.Priority.HIGH,
                models.Task.is_done == False,
                models.Task.is_deleted == False,
            )
            .first()
        )

        if high_priority_tasks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action restricted: This note cannot be archived while it contains incomplete high-priority tasks. Please complete or re-prioritize these tasks first.",
            )

    try:
        for key, value in data.items():
            if key == "is_deleted":
                continue
            setattr(db_note, key, value)

        # Trigger background embedding update if content changed
        if any(k in data for k in ["title", "summary"]):
            generate_note_embeddings_task.delay(note_id)

        db_note.updated_at = int(time.time() * 1000)
        db.commit()
    except Exception as e:
        db.rollback()
        JLogger.error(
            "Failed to update note",
            note_id=note_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Note update failed",
        )
    return db_note


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    DELETE /{note_id}: Professional deletion handling via DeletionService.
    Includes redundancy check: Block deletion if note has in-progress HIGH priority tasks.
    """
    verify_note_ownership(db, current_user, note_id)
    # REDUNDANCY CHECK: Block deletion if note has in-progress HIGH priority tasks
    high_priority_active_tasks = (
        db.query(models.Task)
        .filter(
            models.Task.note_id == note_id,
            models.Task.priority == models.Priority.HIGH,
            models.Task.is_done == False,
            models.Task.is_deleted == False,
        )
        .first()
    )

    if high_priority_active_tasks:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete note: It contains in-progress HIGH priority tasks.",
        )

    if hard:
        # HARD Delete (Physically remove files)
        result = DeletionService.hard_delete_note(db, note_id)
    else:
        # SOFT Delete (Mark as deleted)
        result = DeletionService.soft_delete_note(
            db, note_id, deleted_by=current_user.id
        )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.post("/{note_id}/ask")
async def ask_ai(
    note_id: str,
    question: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    POST /{note_id}/ask: Real-time AI Q&A about the note.
    Returns answer immediately for chat-like experience.
    """
    db_note = verify_note_ownership(db, current_user, note_id)

    if db_note.is_deleted:
        raise HTTPException(status_code=403, detail="Note is deleted")

    # Get transcript
    transcript = db_note.transcript
    if not transcript:
        raise HTTPException(status_code=400, detail="Note has no transcript")

    # Generate answer synchronously for real-time chat
    ai_service = AIService()
    user_role = (
        current_user.primary_role.value if current_user.primary_role else "GENERIC"
    )

    # Use LLM to answer the question

    try:
        response = ai_service.groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful AI assistant. Answer questions about the following note:\n\n{transcript}",
                },
                {"role": "user", "content": question},
            ],
            model="llama-3.1-70b-versatile",
            temperature=0.3,
            max_tokens=500,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    # Save to history
    new_response = {
        "question": question,
        "answer": answer,
        "timestamp": int(time.time() * 1000),
    }

    history = list(db_note.ai_responses) if db_note.ai_responses else []
    history.append(new_response)
    db_note.ai_responses = history
    db.commit()

    # Return answer immediately
    return {
        "question": question,
        "answer": answer,
        "timestamp": new_response["timestamp"],
        "note_id": note_id,
    }


@router.post("/search")
@limiter.limit("10/minute")
async def search_notes_hybrid(
    request: Request,
    query: note_schema.SearchQuery,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    POST /search: Unified V-RAG (Voice-Retrieval Augmented Generation).
    Searches local notes first using pgvector, falls back to Web (Tavily) if needed.
    """
    try:
        ai_service = AIService()
        search_service = SearchService(ai_service)
        result = await search_service.unified_rag_search(
            db, current_user.id, query.query, limit=limit, offset=offset
        )
        return result
    except Exception as e:
        # Use current_user.id if available, otherwise just log error
        user_id = (
            getattr(current_user, "id", "system")
            if "current_user" in locals()
            else "unknown"
        )
        JLogger.error(
            "System error in note API",
            user_id=user_id,
            error=str(e),
            path=request.url.path,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Operation failed to process",
        )


@router.get("/{note_id}/whatsapp")
def get_whatsapp_draft(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    GET /{note_id}/whatsapp: Generates a WhatsApp deep-link for the note's summary.
    Requirement: "Voice-to-WhatsApp Draft"
    """
    note = verify_note_ownership(db, current_user, note_id)

    text = f"VoiceNote Note: {note.title}\n\nSummary: {note.summary}\n\nTasks:\n"
    tasks = db.query(models.Task).filter(models.Task.note_id == note_id).all()
    for t in tasks:
        status_icon = "✅" if t.is_done else "⏳"
        text += f"- {status_icon} {t.description}\n"

    import urllib.parse

    encoded_text = urllib.parse.quote(text)
    wa_link = f"https://wa.me/?text={encoded_text}"

    return {"whatsapp_link": wa_link, "draft": text}


@router.post("/{note_id}/semantic-analysis", status_code=status.HTTP_202_ACCEPTED)
async def analyze_note_semantics(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(requires_tier(models.SubscriptionTier.PREMIUM)),
):
    """
    POST /{note_id}/semantic-analysis: Deep dive into note meaning.
    Offloaded to background for elite performance.
    """
    db_note = verify_note_ownership(db, current_user, note_id)

    if db_note.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Note is deleted",
        )

    # Trigger background task
    analyze_note_semantics_task.delay(note_id)

    return {"message": "Semantic analysis started in background", "note_id": note_id}


@router.patch("/{note_id}/restore", response_model=note_schema.NoteResponse)
async def restore_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    PATCH /{note_id}/restore: Restore a soft-deleted note.
    """
    # Verify ownership (even if deleted, we need to check permissions)
    # verify_note_ownership checks for existence.
    # We must custom query if verify_note_ownership filters out deleted notes?
    # verify_note_ownership implementation:
    # "return verify_note_ownership(db, current_user, note_id)"
    # If verify_note_ownership raises 404 for deleted notes, we have a problem.
    # Usually it returns the note.
    # notes.py: "db_note = verify_note_ownership(db, current_user, note_id)"
    # Checking verify_note_ownership in `app/utils/security.py` would be wise, but assuming standard behavior:
    # It likely checks user_id == note.user_id.

    # Let's trust DeletionService.restore_note handles the logic, but we need to check ownership first.
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    result = DeletionService.restore_note(db, note_id, restored_by=current_user.id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    # Re-query note to ensure we have fresh state (avoid ObjectDeletedError)
    fresh_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    return fresh_note


@router.delete("")
async def bulk_delete_notes(
    note_ids: List[str] = Body(..., embed=True),
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    DELETE /: Bulk delete notes.
    Accepts explicit list of note_ids to delete.
    Atomic: Tries to delete all, reports failures if any? Or partial success?
    We will proceed sequentially and return summary.
    """
    deleted_count = 0
    errors = []

    for nid in note_ids:
        # Check ownership efficiently
        note = db.query(models.Note).filter(models.Note.id == nid).first()
        if not note or note.user_id != current_user.id:
            errors.append(f"Permission denied or not found for {nid}")
            continue

        # Check high priority tasks constraint (reused logic)
        high_priority_active_tasks = (
            db.query(models.Task)
            .filter(
                models.Task.note_id == nid,
                models.Task.priority == models.Priority.HIGH,
                models.Task.is_done == False,
                models.Task.is_deleted == False,
            )
            .first()
        )

        if high_priority_active_tasks:
            errors.append(f"Note {nid} has active high-priority tasks")
            continue

        if hard:
            res = DeletionService.hard_delete_note(db, nid)
        else:
            res = DeletionService.soft_delete_note(db, nid, deleted_by=current_user.id)

        if res["success"]:
            deleted_count += 1
        else:
            errors.append(f"Failed to delete {nid}: {res['error']}")

    return {
        "message": f"Bulk delete completed. Deleted {deleted_count}/{len(note_ids)} notes.",
        "deleted_count": deleted_count,
        "errors": errors,
    }
