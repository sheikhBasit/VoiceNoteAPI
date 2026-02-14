import os
import time
from typing import List

from fastapi import APIRouter, Depends, Request, Body, HTTPException
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas import note as note_schema
from app.services.ai_service import AIService
from app.services.auth_service import get_current_user
from app.utils.json_logger import JLogger
from app.utils.user_roles import is_admin

router = APIRouter(prefix="/api/v1/ai", tags=["AI & Insights"])
# ai_service is instantiated inside endpoints to avoid module-level hangs
# ai_service = AIService()

from app.core.limiter import limiter
ai_service = AIService()


@router.post("/search", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
async def semantic_search_handler(
    request: Request,
    query: str = Body(..., embed=True),
    limit: int = Body(5, embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Search endpoint using consolidated semantic search logic.
    """
    results_with_scores = ai_service.perform_semantic_search(
        db, 
        current_user.id, 
        query, 
        limit=limit, 
        is_admin=is_admin(current_user)
    )
    
    # Return just the notes for this response model (NoteResponse)
    return [r["note"] for r in results_with_scores]


@router.post("/ask")
@limiter.limit("30/minute")
async def ask_ai_custom(
    request: Request,
    question: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    POST /ask: Global AI assistant with RAG context.
    Uses unified AIService logic.
    """
    try:
        answer = ai_service.answer_question(db, current_user.id, question)
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_user_stats(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    GET /stats: Dashboard Insights.
    Returns high-level stats like '5 High Priority tasks today'.
    """
    user_id = current_user.id

    # Admin gets global stats, user gets their own
    task_query = db.query(models.Task).filter(
        models.Task.priority == models.Priority.HIGH,
        models.Task.is_done == False,
        models.Task.is_deleted == False,
    )

    note_query = db.query(models.Note).filter(models.Note.is_deleted == False)

    if not is_admin(current_user):  # Using new utility function
        task_query = task_query.filter(models.Task.user_id == user_id)
        note_query = note_query.filter(models.Note.user_id == user_id)

    high_priority_count = task_query.count()
    total_notes = note_query.count()

    return {
        "high_priority_pending_tasks": high_priority_count,
        "total_active_notes": total_notes,
        "scope": (
            "GLOBAL" if is_admin(current_user) else "PRIVATE"
        ),  # Using new utility function
        "suggestion": f"You have {high_priority_count} critical items. Should I summarize them?",
    }
