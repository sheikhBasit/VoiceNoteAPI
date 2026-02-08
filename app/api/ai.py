import os
import time
from typing import List

from fastapi import APIRouter, Depends, Request, Body
from slowapi import Limiter
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

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)
ai_service = AIService()


@router.post("/search", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
async def semantic_search(
    request: Request,
    query: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    user_id = current_user.id
    start_time = time.time()
    query_vector = ai_service.generate_embedding_sync(query)
    embedding_time = time.time() - start_time

    # EXEMPTION: Admins can search across all notes
    query_obj = db.query(models.Note).filter(
        models.Note.is_deleted == False, models.Note.is_encrypted == False
    )

    if not is_admin(current_user):  # Using new utility function
        query_obj = query_obj.filter(models.Note.user_id == user_id)

    # Use cosine_distance to match the HNSW index (vector_cosine_ops)
    results = (
        query_obj.order_by(models.Note.embedding.cosine_distance(query_vector))
        .limit(5)
        .all()
    )

    search_time = time.time() - (start_time + embedding_time)

    JLogger.info(
        "Semantic search performed",
        user_id=user_id,
        is_admin=is_admin(current_user),
        query=query,
        results_count=len(results),
        embedding_time_ms=int(embedding_time * 1000),
        search_time_ms=int(search_time * 1000),
    )

    return results


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
