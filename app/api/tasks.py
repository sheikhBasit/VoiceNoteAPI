from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import uuid
import time
import os

from app.db.session import get_db
from app.db import models
from app.schemas import task as task_schema
from app.services.auth_service import get_current_user
from app.worker.task import process_task_image_pipeline
from app.services.deletion_service import DeletionService
from app.utils.security import verify_note_ownership, verify_task_ownership
from app.utils.json_logger import JLogger
from app.services.task_service import TaskService
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL", "redis://redis:6379/0"))
router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

@router.post("", response_model=task_schema.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: task_schema.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """POST /: Create a new task directly (not from AI extraction)."""
    # ✅ Verify ownership if note_id provided
    if task_data.note_id:
        verify_note_ownership(db, current_user, task_data.note_id)
    # ✅ Validate description is not empty after strip
    description = task_data.description.strip()
    if not description or len(description) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Validation failed: Task description cannot be empty"
        )
    if len(description) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Validation failed: Task description exceeds maximum length of 2000 characters"
        )
    
    # Verify the note exists if note_id is provided
    if task_data.note_id:
        note = db.query(models.Note).filter(models.Note.id == task_data.note_id).first()
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Resource not found: Associated note with ID '{task_data.note_id}' missing or invalid"
            )
    
    new_task = models.Task(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        note_id=task_data.note_id,
        description=description,
        priority=task_data.priority,
        deadline=task_data.deadline,
        assigned_entities=[e.dict(exclude_unset=True) for e in task_data.assigned_entities],
        image_uris=list(task_data.image_uris),
        document_uris=list(task_data.document_uris),
        external_links=[e.dict(exclude_unset=True) for e in task_data.external_links],
        communication_type=task_data.communication_type,
        is_action_approved=task_data.is_action_approved,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    )
    try:
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        JLogger.info("Task created manually", task_id=new_task.id, user_id=current_user.id, note_id=task_data.note_id)
    except Exception as e:
        db.rollback()
        JLogger.error("Failed to persist manual task", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Task creation failed"
        )
    return new_task

@router.get("", response_model=List[task_schema.TaskResponse])
def list_tasks(
    user_id: Optional[str] = Query(None, description="Filter by User ID (Admin Only)"),
    note_id: Optional[str] = Query(None, description="Filter by Note ID"),
    email: Optional[str] = Query(None, description="Filter by Assigned Contact Email"),
    phone: Optional[str] = Query(None, description="Filter by Assigned Contact Phone"),
    priority: Optional[models.Priority] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    GET /: Returns active tasks with flexible filtering.
    - Admins: See all tasks or filter by user_id.
    - Regular Users: See only their own tasks.
    - Filtering: Support for note_id, contact email, and contact phone.
    """
    query = db.query(models.Task).options(
        joinedload(models.Task.note)
    ).filter(
        models.Task.user_id == current_user.id,
        models.Task.is_deleted == False
    )

    if note_id:
        query = query.filter(models.Task.note_id == note_id)
    
    if email:
        query = query.filter(models.Task.assigned_entities.contains([{"email": email}]))
    
    if phone:
        query = query.filter(models.Task.assigned_entities.contains([{"phone": phone}]))

    if priority:
        query = query.filter(models.Task.priority == priority)
    
    return query.limit(limit).offset(offset).all()

@router.get("/due-today", response_model=List[task_schema.TaskResponse])
def get_tasks_due_today(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /due-today: Get only tasks with deadline today for user."""
    from datetime import datetime, time as dt_time
    from zoneinfo import ZoneInfo
    
    user_tz = ZoneInfo(current_user.timezone or "UTC")
    now_user = datetime.fromtimestamp(time.time(), tz=user_tz)
    
    # Start and End of "Today" in user's local timezone
    today_start = datetime.combine(now_user.date(), dt_time.min).replace(tzinfo=user_tz)
    today_end = datetime.combine(now_user.date(), dt_time.max).replace(tzinfo=user_tz)
    
    # Convert back to Unix epoch milliseconds for DB comparison
    start_ms = int(today_start.timestamp() * 1000)
    end_ms = int(today_end.timestamp() * 1000)
    
    tasks = db.query(models.Task).filter(
        models.Task.user_id == current_user.id,
        models.Task.is_deleted == False,
        models.Task.is_done == False,
        models.Task.deadline >= start_ms,
        models.Task.deadline <= end_ms
    ).order_by(models.Task.priority.desc()).limit(limit).offset(offset).all()
    
    return tasks


@router.get("/overdue", response_model=List[task_schema.TaskResponse])
def get_overdue_tasks(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /overdue: Get all overdue tasks (past deadline) for user."""
    current_time = int(time.time() * 1000)
    
    tasks = db.query(models.Task).filter(
        models.Task.user_id == current_user.id,
        models.Task.is_deleted == False,
        models.Task.is_done == False,
        models.Task.deadline < current_time,
        models.Task.deadline.isnot(None)
    ).order_by(models.Task.priority.desc()).limit(limit).offset(offset).all()
    
    return tasks


@router.get("/assigned-to-me", response_model=List[task_schema.TaskResponse])
def get_tasks_assigned_to_me(
    user_email: Optional[str] = None,
    user_phone: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /assigned-to-me: Get tasks assigned to current user (validated)."""
    # Force search only for current user's own identity for security
    search_email = user_email or current_user.email
    search_phone = user_phone # Phone can be optional/different
    
    query = db.query(models.Task).filter(
        models.Task.user_id == current_user.id, # Filter by ownership first
        models.Task.is_deleted == False
    )
    
    if search_email:
        query = query.filter(
            models.Task.assigned_entities.contains([{"email": search_email}])
        )
    if search_phone:
        query = query.filter(
            models.Task.assigned_entities.contains([{"phone": search_phone}])
        )
    
    return query.limit(limit).offset(offset).all()


@router.get("/search", response_model=List[task_schema.TaskResponse])
def search_tasks(
    query_text: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /search: Full-text search tasks by description or assigned entities."""
    if not query_text or len(query_text.strip()) < 1:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    # Search in description (case-insensitive)
    search_pattern = f"%{query_text}%"
    
    tasks = db.query(models.Task).filter(
        models.Task.user_id == current_user.id,
        models.Task.is_deleted == False,
        models.Task.description.ilike(search_pattern)
    ).limit(limit).offset(offset).all()
    
    return tasks


@router.get("/stats", tags=["Analytics"])
def get_task_statistics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /stats: Get task statistics for dashboard."""
    service = TaskService(db)
    return service.get_task_statistics(current_user.id)



@router.get("/{task_id}", response_model=task_schema.TaskResponse)
def get_single_task(task_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """GET /{task_id}: Returns details of a specific task."""
    # 1. Existence Check
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found")
    
    # 2. Ownership Check
    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied: You do not own this task")
        
    if task.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Resource deleted: This task has been removed and must be restored before access"
        )
        
    return task

@router.patch("/{task_id}", response_model=task_schema.TaskResponse)
def update_task(
    task_id: str,
    task_update: task_schema.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    PATCH /{task_id}: Unified update for task details.
    Handles description, priority, deadline, status, assignments, and soft deletion.
    """
    task = verify_task_ownership(db, current_user, task_id)
    
    # Update only provided fields
    update_data = task_update.model_dump(exclude_unset=True)
    
    # Validation for deadline
    if "deadline" in update_data and update_data["deadline"]:
        current_time = int(time.time() * 1000)
        if update_data["deadline"] < current_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Validation failed: Task deadline must be a future timestamp"
            )

    # Handle soft deletion/restore via update
    if "is_deleted" in update_data:
        if update_data["is_deleted"]:
            DeletionService.soft_delete_task(db, task_id, deleted_by=current_user.id)
            db.refresh(task) # Ensure we return the state after deletion service
            return task
        else:
            task.is_deleted = False
            task.deleted_at = None

    try:
        for key, value in update_data.items():
            if key == "is_deleted": continue # Handled above
            
            if key == "assigned_entities" and value is not None:
                task.assigned_entities = [e.dict(exclude_unset=True) for e in value]
            elif key == "external_links" and value is not None:
                task.external_links = [e.dict(exclude_unset=True) for e in value]
            elif key == "image_uris" and value is not None:
                task.image_uris = list(value)
            elif key == "document_uris" and value is not None:
                task.document_uris = list(value)
            else:
                setattr(task, key, value)
        
        task.updated_at = int(time.time() * 1000)
        db.commit()
        db.refresh(task)
    except Exception as e:
        db.rollback()
        JLogger.error("Task patch failed in database", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error: Task update could not be persisted"
        )
    return task


@router.post("/{task_id}/multimedia")
async def add_task_multimedia(
    task_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    POST: Upload image/doc and offload processing to background.
    Optimized: Immediate response to user while worker handles compression.
    """
    task = verify_task_ownership(db, current_user, task_id)

    # 1. Save locally via chunked reading
    temp_id = str(uuid.uuid4())
    local_path = f"uploads/task_{temp_id}_{file.filename}"
    max_size = 10 * 1024 * 1024 # 10MB for task images
    total_size = 0
    
    with open(local_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            total_size += len(chunk)
            if total_size > max_size:
                os.remove(local_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, 
                    detail="File too large: Multimedia uploads are limited to 10MB per file"
                )
            buffer.write(chunk)

    # 2. Offload to Celery: Handles compression and Cloudinary
    # This prevents the API from hanging during slow uploads
    process_task_image_pipeline.delay(task_id, local_path, file.filename)

    return {"message": "Upload received. Processing in background.", "task_id": task_id}


@router.delete("/{task_id}")
def delete_task(task_id: str, hard: bool = False, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """DELETE /{task_id}: Professional deletion handling via DeletionService."""
    verify_task_ownership(db, current_user, task_id)
        
    result = DeletionService.soft_delete_task(db, task_id, deleted_by=current_user.id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return result



@router.patch("/{task_id}/multimedia")
async def remove_multimedia(
    task_id: str,
    payload: dict, # {"url_to_remove": "..."}
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    PATCH: Efficiently remove a specific URL from the JSONB arrays.
    """
    url_to_remove = payload.get("url_to_remove")
    if not url_to_remove:
        raise HTTPException(status_code=400, detail="Missing url_to_remove in request body")

    task = verify_task_ownership(db, current_user, task_id)

    # Filter out the URL from both image and document arrays
    if url_to_remove in task.image_uris:
        task.image_uris = [u for u in task.image_uris if u != url_to_remove]
    elif url_to_remove in task.document_uris:
        task.document_uris = [u for u in task.document_uris if u != url_to_remove]
    
    db.commit()
    return {"message": "Resource removed successfully"}


# ============ COMMUNICATION MANAGEMENT ============



@router.get("/{task_id}/communication-options")
def get_communication_options(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """GET /{task_id}/communication-options: Get available communication channels for assigned entities."""
    task = verify_task_ownership(db, current_user, task_id)
    
    if not task.assigned_entities:
        return {
            "available_channels": [],
            "message": "No entities assigned to this task"
        }
    
    # Determine available communication options based on assigned entities
    available_channels = set()
    
    for entity in task.assigned_entities:
        if entity.get("phone"):
            available_channels.add("WHATSAPP")
            available_channels.add("SMS")
            available_channels.add("CALL")
        if entity.get("email"):
            available_channels.add("SLACK")
            available_channels.add("EMAIL")
    
    return {
        "available_channels": sorted(list(available_channels)),
        "assigned_entities": task.assigned_entities,
        "current_communication_type": task.communication_type
    }


# ============ EXTERNAL LINKS MANAGEMENT ============

@router.post("/{task_id}/external-links", status_code=status.HTTP_201_CREATED)
def add_external_link(
    task_id: str,
    link: task_schema.LinkEntity,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """POST /{task_id}/external-links: Add external link/reference to task."""
    task = verify_task_ownership(db, current_user, task_id)
    
    # Append to external_links array
    new_link = link.dict(exclude_unset=True)
    task.external_links.append(new_link)
    
    db.commit()
    return {
        "message": "External link added",
        "link": new_link,
        "total_links": len(task.external_links)
    }


@router.delete("/{task_id}/external-links/{link_index}")
def remove_external_link(
    task_id: str,
    link_index: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """DELETE /{task_id}/external-links/{link_index}: Remove specific external link."""
    task = verify_task_ownership(db, current_user, task_id)
    
    if link_index < 0 or link_index >= len(task.external_links):
        raise HTTPException(status_code=400, detail="Invalid link index")
    
    removed_link = task.external_links.pop(link_index)
    db.commit()
    
    return {
        "message": "External link removed",
        "removed_link": removed_link,
        "remaining_links": len(task.external_links)
    }


# ============ FILTERING & SEARCH ============



# ============ TASK MANAGEMENT UTILITIES ============



@router.post("/{task_id}/duplicate", response_model=task_schema.TaskResponse, status_code=status.HTTP_201_CREATED)
def duplicate_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """POST /{task_id}/duplicate: Create a copy of existing task."""
    original_task = verify_task_ownership(db, current_user, task_id)
    
    # Create duplicate task
    duplicate = models.Task(
        id=str(uuid.uuid4()),
        note_id=original_task.note_id,
        description=original_task.description,
        priority=original_task.priority,
        deadline=original_task.deadline,
        assigned_entities=original_task.assigned_entities.copy(),
        image_uris=original_task.image_uris.copy(),
        document_uris=original_task.document_uris.copy(),
        external_links=original_task.external_links.copy(),
        communication_type=original_task.communication_type,
        is_action_approved=False,  # Reset approval status
        is_done=False,  # Reset completion status
        created_at=int(time.time() * 1000)
    )
    
    db.add(duplicate)
    db.commit()
    db.refresh(duplicate)
    
    return duplicate


# ============ STATISTICS & ANALYTICS ============

