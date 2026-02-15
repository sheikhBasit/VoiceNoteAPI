import time
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
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

    model_config = {"from_attributes": True}


# --- Endpoints ---


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new folder for organizing notes."""
    existing = (
        db.query(models.Folder)
        .filter(
            models.Folder.user_id == current_user.id,
            models.Folder.name == folder_data.name,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400, detail="Folder with this name already exists"
        )

    new_folder = models.Folder(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=folder_data.name,
        color=folder_data.color,
        icon=folder_data.icon,
        created_at=int(time.time() * 1000),
        updated_at=int(time.time() * 1000),
    )
    db.add(new_folder)
    db.commit()
    db.refresh(new_folder)

    JLogger.info("Folder created", folder_id=new_folder.id, user_id=current_user.id)
    return new_folder


@router.get("", response_model=List[FolderResponse])
def list_folders(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """
    List all folders for the current user including shared ones.
    Docstring: Avoids N+1 by using a subquery for note counts and eager loading relationships.
    """
    from sqlalchemy import func
    from sqlalchemy.orm import aliased

    # Subquery for note counts to avoid N+1
    note_count_sub = (
        db.query(models.Note.folder_id, func.count(models.Note.id).label("count"))
        .filter(models.Note.is_deleted == False)
        .group_by(models.Note.folder_id)
        .subquery()
    )

    # 1. Folders owned by the user
    owned_folders = (
        db.query(models.Folder, note_count_sub.c.count)
        .outerjoin(note_count_sub, models.Folder.id == note_count_sub.c.folder_id)
        .filter(models.Folder.user_id == current_user.id)
        .all()
    )

    # 2. Folders shared with the user (via folder_participants M2M)
    shared_folders_query = (
        db.query(models.Folder, note_count_sub.c.count)
        .outerjoin(note_count_sub, models.Folder.id == note_count_sub.c.folder_id)
        .join(models.folder_participants, models.Folder.id == models.folder_participants.c.folder_id)
        .filter(models.folder_participants.c.user_id == current_user.id)
        .all()
    )

    combined_folders = owned_folders + shared_folders_query
    
    # Dedup and Format Response
    response = []
    seen_ids = set()
    for f, count in combined_folders:
        if f.id in seen_ids:
            continue
        seen_ids.add(f.id)
        
        resp = FolderResponse.model_validate(f)
        resp.note_count = count or 0
        response.append(resp)

    return response


@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(
    folder_id: str,
    update_data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Update folder details."""
    folder = (
        db.query(models.Folder)
        .filter(models.Folder.id == folder_id, models.Folder.user_id == current_user.id)
        .first()
    )

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
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete a folder.
    Notes inside it are NOT deleted but moved to 'Uncategorized' (folder_id=None).
    """
    folder = (
        db.query(models.Folder)
        .filter(models.Folder.id == folder_id, models.Folder.user_id == current_user.id)
        .first()
    )

    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Unlink notes (Set folder_id to NULL)
    db.query(models.Note).filter(models.Note.folder_id == folder_id).update(
        {"folder_id": None}, synchronize_session="fetch"
    )
    db.flush()

    db.delete(folder)
    db.commit()

    JLogger.info("Folder deleted", folder_id=folder_id, user_id=current_user.id)
    return {"message": "Folder deleted successfully"}
