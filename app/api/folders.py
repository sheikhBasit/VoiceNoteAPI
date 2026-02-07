from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import time
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.db import models
from app.services.auth_service import get_current_user
from app.utils.json_logger import JLogger

router = APIRouter(prefix="/api/v1/folders", tags=["Folders"])

# --- Schemas ---
class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = "#FFFFFF"
    icon: Optional[str] = "folder"

class FolderUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

class FolderResponse(BaseModel):
    id: str
    name: str
    color: str
    icon: str
    created_at: int
    updated_at: int
    note_count: int = 0

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new folder for organizing notes."""
    existing = db.query(models.Folder).filter(
        models.Folder.user_id == current_user.id,
        models.Folder.name == folder_data.name
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Folder with this name already exists")

    new_folder = models.Folder(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=folder_data.name,
        color=folder_data.color,
        icon=folder_data.icon,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000)
    )
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)
    
    JLogger.info("Folder created", folder_id=new_folder.id, user_id=current_user.id)
    return new_folder

@router.get("", response_model=List[FolderResponse])
def list_folders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List all folders for the current user with note counts."""
    folders = db.query(models.Folder).filter(models.Folder.user_id == current_user.id).all()
    
    # Calculate note counts
    response = []
    for f in folders:
        count = db.query(models.Note).filter(
            models.Note.folder_id == f.id,
            models.Note.is_deleted == False
        ).count()
        
        # Serialize manually to include dynamic note_count
        resp = FolderResponse.model_validate(f)
        resp.note_count = count
        response.append(resp)
        
    return response

@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: str,
    update_data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update folder details."""
    folder = db.query(models.Folder).filter(
        models.Folder.id == folder_id,
        models.Folder.user_id == current_user.id
    ).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(folder, key, value)
        
    folder.updated_at = int(time.time() * 1000)
    db.commit()
    db.refresh(folder)
    return folder

@router.delete("/{folder_id}")
def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Delete a folder. 
    Notes inside it are NOT deleted but moved to 'Uncategorized' (folder_id=None).
    """
    folder = db.query(models.Folder).filter(
        models.Folder.id == folder_id,
        models.Folder.user_id == current_user.id
    ).first()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    # Unlink notes (Set folder_id to NULL)
    db.query(models.Note).filter(models.Note.folder_id == folder_id).update({"folder_id": None})
    
    db.delete(folder)
    db.commit()
    
    JLogger.info("Folder deleted", folder_id=folder_id, user_id=current_user.id)
    return {"message": "Folder deleted successfully"}
