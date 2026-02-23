import os
import urllib.parse
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
from app.core.limiter import limiter
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas import note as note_schema
from app.services.auth_service import get_current_user
from app.services.note_service import NoteService
from app.utils.billing_utils import check_credit_balance, requires_tier
from app.utils.security import verify_device_signature
from app.services.deletion_service import DeletionService
from app.services.ai_service import AIService
from app.services.search_service import SearchService
from app.services.storage_service import StorageService

# Services are instantiated inside endpoints to avoid module-level hangs

router = APIRouter(prefix="/api/v1/notes", tags=["Notes"])


@router.get("/presigned-url")
async def get_presigned_url(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    GET /presigned-url: Generate a direct-to-storage upload link.
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
            detail="Could not generate upload link.",
        )


@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def process_note(
    request: Request,
    file: Optional[UploadFile] = File(None),
    storage_key: Optional[str] = Form(None),
    note_id_override: Optional[str] = Form(None),
    mode: Optional[str] = Form("GENERIC"),
    languages: Optional[str] = Form(None),
    stt_model: Optional[str] = Form("nova"),
    document_uris: Optional[str] = Form(None),
    image_uris: Optional[str] = Form(None),
    team_id: Optional[str] = Form(None),
    debug_sync: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(requires_tier(models.SubscriptionTier.FREE)),
    _balance: bool = Depends(check_credit_balance(10)),
    _sig: bool = Depends(verify_device_signature),
):
    """POST /process: Main Upload for audio processing."""
    return await NoteService.process_note_upload(
        db, current_user, file, storage_key, note_id_override, 
        mode, languages, stt_model, document_uris, image_uris, team_id, debug_sync
    )


@router.post(
    "/create",
    response_model=note_schema.NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_note(
    request: Request,
    note_data: note_schema.NoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(requires_tier(models.SubscriptionTier.FREE)),
    _balance: bool = Depends(check_credit_balance(5)),
):
    """POST /create: Manually create a note record (requires FREE tier+)."""
    note_dict = note_data.model_dump()
    return NoteService.create_note_record(db, current_user, note_dict)


@router.get("/dashboard", response_model=note_schema.DashboardResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """GET /dashboard: Unified productivity metrics."""
    return NoteService.get_dashboard_metrics(db, current_user.id)


@router.get("/autocomplete", response_model=List[str])
def search_autocomplete(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /autocomplete: Suggest note titles."""
    return NoteService.search_autocomplete(db, current_user, q)


@router.patch("/move")
def bulk_move_notes(
    note_ids: List[str] = Body(..., embed=True),
    folder_id: Optional[str] = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """PATCH /move: Bulk move notes."""
    return NoteService.bulk_move_notes(db, current_user, note_ids, folder_id)


@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /: Returns accessible notes for the user."""
    return NoteService.list_notes(db, current_user, skip, limit)
@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(
    note_id: str,
    verbose: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /{note_id}: Returns full note detail."""
    return NoteService.get_note(db, current_user, note_id, verbose)


@router.patch("/{note_id}", response_model=note_schema.NoteResponse)
async def update_note(
    note_id: str,
    update_data: note_schema.NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """PATCH /{note_id}: Update note details."""
    data = update_data.model_dump(exclude_unset=True)
    return NoteService.update_note(db, current_user, note_id, data)


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """DELETE /{note_id}: Delete a note."""
    if hard:
        if not current_user.is_admin:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: Only administrators can permanently delete notes",
            )
        return DeletionService.hard_delete_note(db, note_id)
    
    NoteService.soft_delete_note(db, current_user, note_id)
    return {"message": "Note moved to trash"}


@router.post("/{note_id}/ask")
async def ask_ai(
    note_id: str,
    question: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """POST /{note_id}/ask: AI Q&A about the note."""
    # Ensure access
    NoteService.verify_note_access(db, current_user, note_id)
    
    ai_service = AIService()
    answer = ai_service.answer_question(db, current_user.id, question, note_id=note_id)
    return {"answer": answer}


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
    """POST /search: Hybrid semantic search."""
    ai_service = AIService()
    search_service = SearchService(ai_service)
    return await search_service.unified_rag_search(
        db, current_user.id, query.query, limit=limit, offset=offset
    )


@router.post("/{note_id}/semantic-analysis", status_code=status.HTTP_202_ACCEPTED)
async def semantic_analysis(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    POST /{note_id}/semantic-analysis: Trigger manual analysis.
    Returns 202 Accepted as it offloads to Celery.
    """
    return NoteService.trigger_semantic_analysis(db, current_user, note_id)


@router.get("/{note_id}/whatsapp")
def get_whatsapp_draft(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """GET /{note_id}/whatsapp: Generate WhatsApp draft."""
    note = NoteService.get_note(db, current_user, note_id)
    
    text = f"VoiceNote: {note.title}\n\n{note.summary}\n"
    encoded_text = urllib.parse.quote(text)
    return {"whatsapp_link": f"https://wa.me/?text={encoded_text}", "draft": text}


@router.patch("/{note_id}/restore", response_model=note_schema.NoteResponse)
async def restore_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """PATCH /{note_id}/restore: Restore from trash."""
    NoteService.restore_note(db, current_user, note_id)
    return NoteService.get_note(db, current_user, note_id)


@router.delete("")
async def bulk_delete_notes(
    note_ids: List[str] = Body(..., embed=True),
    hard: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """DELETE /: Bulk delete notes."""
    return NoteService.bulk_delete_notes(db, current_user, note_ids, hard)
