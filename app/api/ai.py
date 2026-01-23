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
from fastapi import Request

router = APIRouter(prefix="/api/v1/ai", tags=["AI & Insights"])
ai_service = AIService()

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0")
@router.post("/search", response_model=List[note_schema.NoteResponse])
@limiter.limit("5/hour")
async def semantic_search(request: Request, query: str, user_id: str, db: Session = Depends(get_db)):
    query_vector = ai_service.generate_embedding(query)
    
    # Strictly filter by user_id and is_deleted before calculating distance
    results = db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == False,
        models.Note.is_encrypted == False # Assuming AI can't read encrypted notes
    ).order_by(
        models.Note.embedding.l2_distance(query_vector)
    ).limit(5).all()
    
    return results

@router.get("/stats")
def get_user_stats(user_id: str, db: Session = Depends(get_db)):
    """
    GET /stats: Dashboard Insights.
    Returns high-level stats like '5 High Priority tasks today'.
    """
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