from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import time

from app.db.session import get_db
from app.db import models
from app.schemas import task as task_schema
from app.services.cloudinary_service import CloudinaryService
from app.worker.task import process_task_image_pipeline
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0")
router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])
cloudinary_service = CloudinaryService()

@router.post("", response_model=task_schema.TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    task_data: task_schema.TaskCreate,
    db: Session = Depends(get_db)
):
    """POST /: Create a new task directly (not from AI extraction)."""
    # ✅ Validate description is not empty after strip
    description = task_data.description.strip()
    if not description or len(description) < 1:
        raise HTTPException(status_code=400, detail="Description cannot be empty")
    if len(description) > 2000:
        raise HTTPException(status_code=400, detail="Description too long (max 2000 characters)")
    
    # Verify the note exists
    note = db.query(models.Note).filter(models.Note.id == task_data.note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Associated note not found")
    
    new_task = models.Task(
        id=str(uuid.uuid4()),
        note_id=task_data.note_id,
        description=description,
        priority=task_data.priority,
        deadline=task_data.deadline,
        assigned_entities=[e.dict(exclude_unset=True) for e in task_data.assigned_entities],
        image_urls=list(task_data.image_urls),
        document_urls=list(task_data.document_urls),
        external_links=[e.dict(exclude_unset=True) for e in task_data.external_links],
        communication_type=task_data.communication_type,
        is_action_approved=task_data.is_action_approved,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

@router.get("", response_model=List[task_schema.TaskResponse])
def list_tasks(
    user_id: str, 
    priority: Optional[models.Priority] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """GET /: Returns all active tasks across all notes with optional priority filter."""
    # ✅ Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    query = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
        models.Task.is_deleted == False
    )
    if priority:
        query = query.filter(models.Task.priority == priority)
    
    # ✅ Add pagination
    return query.limit(limit).offset(offset).all()

@router.get("/{task_id}", response_model=task_schema.TaskResponse)
def get_single_task(task_id: str, db: Session = Depends(get_db)):
    """GET /{task_id}: Returns details of a specific task."""
    task = db.query(models.Task).filter(models.Task.id == task_id,
    models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=task_schema.TaskResponse)
def update_task(
    task_id: str,
    task_update: task_schema.TaskBase,
    db: Session = Depends(get_db)
):
    """PATCH /{task_id}: Update task details (description, priority, deadline, etc.)."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Update only provided fields
    update_data = task_update.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        if key == "assigned_entities" and value is not None:
            # Convert Pydantic models to dicts for JSONB
            task.assigned_entities = [e.dict(exclude_unset=True) for e in value]
        elif key == "external_links" and value is not None:
            task.external_links = [e.dict(exclude_unset=True) for e in value]
        elif key == "image_urls" and value is not None:
            task.image_urls = list(value)
        elif key == "document_urls" and value is not None:
            task.document_urls = list(value)
        else:
            setattr(task, key, value)
    
    # ✅ Update timestamp on modification
    task.updated_at = int(time.time() * 1000)
    
    db.commit()
    db.refresh(task)
    return task

@router.patch("/{task_id}/toggle")
def toggle_task_status(task_id: str, is_done: bool, db: Session = Depends(get_db)):
    """PATCH /{task_id}/toggle: Mark task as isDone."""
    task = db.query(models.Task).filter(models.Task.id == task_id,
    models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_done = is_done
    db.commit()
    return {"message": "Status updated", "is_done": task.is_done}

@router.post("/{task_id}/multimedia")
async def add_task_multimedia(
    task_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    POST: Upload image/doc and offload processing to background.
    Optimized: Immediate response to user while worker handles compression.
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 1. Save locally for the worker to find
    temp_id = str(uuid.uuid4())
    local_path = f"uploads/task_{temp_id}_{file.filename}"
    with open(local_path, "wb") as buffer:
        buffer.write(await file.read())

    # 2. Offload to Celery: Handles compression and Cloudinary
    # This prevents the API from hanging during slow uploads
    process_task_image_pipeline.delay(task_id, local_path, file.filename)

    return {"message": "Upload received. Processing in background.", "task_id": task_id}

@router.patch("/{task_id}/approve")
def approve_action(task_id: str, db: Session = Depends(get_db)):
    """PATCH /{task_id}/approve: Sets isActionApproved for automation."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_action_approved = True
    db.commit()
    return {"message": "Action approved for automation"}

@router.delete("/{task_id}")
def delete_task(task_id: str, hard: bool = False, db: Session = Depends(get_db)):
    """DELETE /{task_id}: Soft delete by default, Hard delete if specified."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if hard:
        db.delete(task)
    else:
        task.is_deleted = True
        task.deleted_at = int(time.time() * 1000)
    
    db.commit()
    return {"message": "Task deleted successfully", "type": "hard" if hard else "soft"}

@router.patch("/{task_id}/assign")
async def assign_task(
    task_id: str,
    assigned_entities: List[task_schema.ContactEntity],
    db: Session = Depends(get_db)
):
    """Assign task with contact entities (name, phone, email)."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Convert Pydantic models to dictionaries for JSONB storage
    task.assigned_entities = [entity.dict(exclude_unset=True) for entity in assigned_entities]
    db.commit()
    
    return {"message": "Task assignment updated", "assigned_entities": task.assigned_entities}

@router.get("/search/assigned", response_model=List[task_schema.TaskResponse])
def get_tasks_by_assignment(
    email: Optional[str] = None, 
    phone: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    """
    GET: Advanced Query for tasks assigned to specific contact.
    Searches within the assigned_entities JSONB array.
    """
    query = db.query(models.Task).filter(models.Task.is_deleted == False)
    
    if email:
        query = query.filter(models.Task.assigned_entities.contains([{"email": email}]))
    if phone:
        query = query.filter(models.Task.assigned_entities.contains([{"phone": phone}]))
        
    return query.all()

@router.patch("/{task_id}/multimedia/remove")
async def remove_multimedia(
    task_id: str,
    url_to_remove: str,
    db: Session = Depends(get_db)
):
    """
    PATCH: Efficiently remove a specific URL from the JSONB arrays.
    """
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Filter out the URL from both image and document arrays
    if url_to_remove in task.image_urls:
        task.image_urls = [u for u in task.image_urls if u != url_to_remove]
    elif url_to_remove in task.document_urls:
        task.document_urls = [u for u in task.document_urls if u != url_to_remove]
    
    db.commit()
    return {"message": "Resource removed successfully"}


# ============ PRIORITY & DEADLINE QUICK ACTIONS ============

@router.patch("/{task_id}/priority")
def update_task_priority(
    task_id: str,
    priority: models.Priority,
    db: Session = Depends(get_db)
):
    """PATCH /{task_id}/priority: Quick update of task priority only."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.priority = priority
    db.commit()
    return {"message": "Priority updated", "priority": priority}


@router.patch("/{task_id}/deadline")
def update_task_deadline(
    task_id: str,
    deadline: int,
    db: Session = Depends(get_db)
):
    """PATCH /{task_id}/deadline: Quick update of task deadline only."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Validate deadline is in future
    current_time = int(time.time() * 1000)
    if deadline < current_time:
        raise HTTPException(status_code=400, detail="Deadline must be in the future")
    
    task.deadline = deadline
    db.commit()
    return {"message": "Deadline updated", "deadline": deadline}


# ============ COMMUNICATION MANAGEMENT ============

@router.patch("/{task_id}/communication-type")
def update_communication_type(
    task_id: str,
    communication_type: models.CommunicationType,
    db: Session = Depends(get_db)
):
    """PATCH /{task_id}/communication-type: Set communication preference for task action."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.communication_type = communication_type
    db.commit()
    return {"message": "Communication type updated", "communication_type": communication_type}


@router.get("/{task_id}/communication-options")
def get_communication_options(
    task_id: str,
    db: Session = Depends(get_db)
):
    """GET /{task_id}/communication-options: Get available communication channels for assigned entities."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
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
    db: Session = Depends(get_db)
):
    """POST /{task_id}/external-links: Add external link/reference to task."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
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
    db: Session = Depends(get_db)
):
    """DELETE /{task_id}/external-links/{link_index}: Remove specific external link."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
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

@router.get("/by-note/{note_id}", response_model=List[task_schema.TaskResponse])
def get_tasks_by_note(
    note_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """GET /by-note/{note_id}: Get all active tasks for a specific note."""
    # Verify note exists
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    tasks = db.query(models.Task).filter(
        models.Task.note_id == note_id,
        models.Task.is_deleted == False
    ).limit(limit).offset(offset).all()
    
    return tasks


@router.get("/due-today", response_model=List[task_schema.TaskResponse])
def get_tasks_due_today(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """GET /due-today: Get only tasks with deadline today for user."""
    # ✅ Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_time = int(time.time() * 1000)
    today_start = (current_time // (24 * 60 * 60 * 1000)) * (24 * 60 * 60 * 1000)
    today_end = today_start + (24 * 60 * 60 * 1000)
    
    tasks = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
        models.Task.is_deleted == False,
        models.Task.is_done == False,
        models.Task.deadline >= today_start,
        models.Task.deadline < today_end
    ).order_by(models.Task.priority.desc()).limit(limit).offset(offset).all()
    
    return tasks


@router.get("/overdue", response_model=List[task_schema.TaskResponse])
def get_overdue_tasks(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """GET /overdue: Get all overdue tasks (past deadline) for user."""
    # ✅ Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_time = int(time.time() * 1000)
    
    tasks = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
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
    db: Session = Depends(get_db)
):
    """GET /assigned-to-me: Get tasks assigned to current user."""
    if not user_email and not user_phone:
        raise HTTPException(
            status_code=400,
            detail="Provide either user_email or user_phone"
        )
    
    query = db.query(models.Task).filter(models.Task.is_deleted == False)
    
    if user_email:
        query = query.filter(
            models.Task.assigned_entities.contains([{"email": user_email}])
        )
    if user_phone:
        query = query.filter(
            models.Task.assigned_entities.contains([{"phone": user_phone}])
        )
    
    return query.limit(limit).offset(offset).all()


@router.get("/search", response_model=List[task_schema.TaskResponse])
def search_tasks(
    user_id: str,
    query_text: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """GET /search: Full-text search tasks by description or assigned entities."""
    # ✅ Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not query_text or len(query_text.strip()) < 1:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
    
    # Search in description (case-insensitive)
    search_pattern = f"%{query_text}%"
    
    tasks = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
        models.Task.is_deleted == False,
        models.Task.description.ilike(search_pattern)
    ).limit(limit).offset(offset).all()
    
    return tasks


# ============ TASK MANAGEMENT UTILITIES ============

@router.patch("/{task_id}/restore")
def restore_soft_deleted_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """PATCH /{task_id}/restore: Restore a soft-deleted task."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if not task.is_deleted:
        return {"message": "Task is not deleted", "task_id": task_id}
    
    task.is_deleted = False
    task.deleted_at = None
    db.commit()
    
    return {"message": "Task restored successfully", "task_id": task_id}


@router.post("/{task_id}/duplicate", response_model=task_schema.TaskResponse, status_code=status.HTTP_201_CREATED)
def duplicate_task(
    task_id: str,
    db: Session = Depends(get_db)
):
    """POST /{task_id}/duplicate: Create a copy of existing task."""
    original_task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not original_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Create duplicate task
    duplicate = models.Task(
        id=str(uuid.uuid4()),
        note_id=original_task.note_id,
        description=original_task.description,
        priority=original_task.priority,
        deadline=original_task.deadline,
        assigned_entities=original_task.assigned_entities.copy(),
        image_urls=original_task.image_urls.copy(),
        document_urls=original_task.document_urls.copy(),
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

@router.get("/stats", tags=["Analytics"])
def get_task_statistics(
    user_id: str,
    db: Session = Depends(get_db)
):
    """GET /stats: Get task statistics for dashboard."""
    # ✅ Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Query all non-deleted tasks for user
    all_tasks = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
        models.Task.is_deleted == False
    ).all()
    
    current_time = int(time.time() * 1000)
    
    # Calculate statistics
    total_tasks = len(all_tasks)
    completed_tasks = len([t for t in all_tasks if t.is_done])
    pending_tasks = total_tasks - completed_tasks
    
    # Tasks by priority
    high_priority = len([t for t in all_tasks if t.priority == models.Priority.HIGH])
    medium_priority = len([t for t in all_tasks if t.priority == models.Priority.MEDIUM])
    low_priority = len([t for t in all_tasks if t.priority == models.Priority.LOW])
    
    # Tasks by deadline
    overdue_tasks = len([
        t for t in all_tasks
        if not t.is_done and t.deadline and t.deadline < current_time
    ])
    
    today_start = (current_time // (24 * 60 * 60 * 1000)) * (24 * 60 * 60 * 1000)
    today_end = today_start + (24 * 60 * 60 * 1000)
    due_today = len([
        t for t in all_tasks
        if not t.is_done and t.deadline and today_start <= t.deadline < today_end
    ])
    
    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "by_priority": {
            "high": high_priority,
            "medium": medium_priority,
            "low": low_priority
        },
        "by_status": {
            "overdue": overdue_tasks,
            "due_today": due_today
        },
        "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
    }


@router.patch("/{task_id}/bulk-update", response_model=task_schema.TaskResponse)
def bulk_update_task(
    task_id: str,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """PATCH /{task_id}/bulk-update: Atomically update multiple task fields."""
    task = db.query(models.Task).filter(
        models.Task.id == task_id,
        models.Task.is_deleted == False
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    try:
        # Validate and update fields
        for key, value in update_data.items():
            if key in ["id", "note_id", "created_at", "is_deleted", "deleted_at"]:
                # Prevent updating critical fields
                continue
            
            if key == "assigned_entities" and value is not None:
                task.assigned_entities = value
            elif key == "external_links" and value is not None:
                task.external_links = value
            elif key == "image_urls" and value is not None:
                task.image_urls = list(value)
            elif key == "document_urls" and value is not None:
                task.document_urls = list(value)
            elif hasattr(task, key):
                setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        return task
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")

