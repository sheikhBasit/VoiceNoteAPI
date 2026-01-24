from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from app.db.session import get_db
from app.db import models
from app.schemas import note as note_schema
from app.services.ai_service import AIService # Service we built earlier
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request, Body, status
from app.utils.json_logger import JLogger
from app.worker.task import process_ai_query_task
from app.services.auth_service import get_current_user
import os

router = APIRouter(prefix="/api/v1/ai", tags=["AI & Insights"])
ai_service = AIService()

limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0"))
@router.post("/search", response_model=List[note_schema.NoteResponse])
@limiter.limit("5/hour")
async def semantic_search(
    request: Request, 
    query: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user_id = current_user.id
    query_vector = ai_service.generate_embedding_sync(query)
    
    # Strictly filter by user_id and is_deleted before calculating distance
    results = db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == False,
        models.Note.is_encrypted == False # Assuming AI can't read encrypted notes
    ).order_by(
        models.Note.embedding.l2_distance(query_vector)
    ).limit(5).all()
    
    JLogger.info("Semantic search performed", 
                 user_id=user_id, 
                 query=query, 
                 results_count=len(results))
    
    return results

    return results

# NOTE: /{note_id}/ask is now unified in notes.py to avoid duplication.

from app.services.auth_service import get_current_user

@router.get("/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    GET /stats: Dashboard Insights.
    Returns high-level stats like '5 High Priority tasks today'.
    """
    user_id = current_user.id
    high_priority_count = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
        models.Task.priority == models.Priority.HIGH,
        models.Task.is_done == False
    ).count()

    total_notes = db.query(models.Note).filter(
        models.Note.user_id == user_id, 
        models.Note.is_deleted == False
    ).count()

    return {
        "high_priority_pending_tasks": high_priority_count,
        "total_active_notes": total_notes,
        "suggestion": f"You have {high_priority_count} critical items. Should I summarize them?"
    }