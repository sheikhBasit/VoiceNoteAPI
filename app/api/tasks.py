from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.db import models
from app.schemas import note_schema # Assuming Task schemas are here
from app.services.cloudinary_service import CloudinaryService
import time
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://redis:6379/0")
router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])
cloudinary_service = CloudinaryService()

@router.get("", response_model=List[note_schema.TaskResponse])
def list_tasks(
    user_id: str, 
    priority: Optional[models.Priority] = None, 
    db: Session = Depends(get_db)
):
    """GET /: Returns all active tasks across all notes with optional priority filter."""
    query = db.query(models.Task).join(models.Note).filter(
        models.Note.user_id == user_id,
        models.Task.is_deleted == False
    )
    if priority:
        query = query.filter(models.Task.priority == priority)
    return query.all()

@router.get("/{task_id}", response_model=note_schema.TaskResponse)
def get_single_task(task_id: str, db: Session = Depends(get_db)):
    """GET /{task_id}: Returns details of a specific task."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}/toggle")
def toggle_task_status(task_id: str, is_done: bool, db: Session = Depends(get_db)):
    """PATCH /{task_id}/toggle: Mark task as isDone."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.is_done = is_done
    db.commit()
    return {"message": "Status updated", "is_done": task.is_done}

@router.post("/{task_id}/image")
@limiter.limit("5/minute")
async def upload_task_image(
    task_id: str, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    """POST /{task_id}/image: Upload and compress image via Cloudinary."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Save temp file for processing
    temp_path = f"uploads/task_{task_id}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    # Use the service we built to compress and upload
    image_url = await cloudinary_service.upload_compressed_image(temp_path, task_id)
    
    task.image_url = image_url
    db.commit()
    
    return {"image_url": image_url}

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