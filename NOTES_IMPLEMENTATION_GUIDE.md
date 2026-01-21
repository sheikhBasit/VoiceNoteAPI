# Notes API - Missing Logic Implementation Guide

**Date:** January 21, 2026  
**Status:** Ready for Implementation  
**Complexity:** Medium  

---

## Quick Summary

The Notes API has **15 identified issues** affecting:
- **Critical:** 1 issue (duplicate route) - blocks API
- **High:** 6 issues (security, validation, consistency)
- **Medium:** 6 issues (features, reliability, validation)
- **Low:** 2 issues (edge cases)

This guide provides step-by-step implementation fixes.

---

## Implementation Plan

### Phase 1: Critical Fixes (1 hour)

#### Fix #1: Remove Duplicate Route Definition
**File:** `app/api/notes.py`  
**Lines:** 87-94 (duplicate), 95-123 (main)  
**Change Type:** Merge function  

**Status:** ❌ BROKEN - Two functions with same route

**Current Problem:**
```python
# Lines 87-94
@router.delete("/{note_id}")
def soft_delete_note(note_id: str, db: Session = Depends(get_db)):
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db_note.is_deleted = True
    db_note.deleted_at = int(time.time() * 1000)
    db.commit()
    return {"message": "Note deleted successfully"}

# Lines 95-123 - OVERWRITES ABOVE!
@router.delete("/{note_id}")  # ❌ SAME ROUTE
def delete_note(note_id: str, hard: bool = False, db: Session = Depends(get_db)):
    # This function replaces the one above
    pass
```

**Fix:** Merge both into single function
```python
@router.delete("/{note_id}")
def delete_note(
    note_id: str,
    user_id: str,  # ✅ Add ownership check
    hard: bool = False,
    db: Session = Depends(get_db)
):
    """DELETE /{note_id}: Soft or hard delete note and associated tasks."""
    
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Verify ownership
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    # ✅ Cascade to Tasks
    tasks = db.query(models.Task).filter(models.Task.note_id == note_id).all()
    
    if hard:
        # Hard Delete Note & Tasks
        for task in tasks:
            db.delete(task)
        db.delete(db_note)
        msg = "Note and all related tasks permanently deleted"
    else:
        # Soft Delete Note & Tasks
        now = int(time.time() * 1000)
        db_note.is_deleted = True
        db_note.deleted_at = now
        for task in tasks:
            task.is_deleted = True
            task.deleted_at = now
        msg = "Note and tasks archived (soft delete)"
    
    db.commit()
    return {"message": msg, "type": "hard" if hard else "soft"}
```

**Testing:**
```python
# Should work for soft delete
DELETE /api/v1/notes/note-123?user_id=user-456&hard=false
# Response: {"message": "Note and tasks archived (soft delete)", "type": "soft"}

# Should work for hard delete
DELETE /api/v1/notes/note-123?user_id=user-456&hard=true
# Response: {"message": "Note and all related tasks permanently deleted", "type": "hard"}

# Should fail - wrong user
DELETE /api/v1/notes/note-123?user_id=wrong-user&hard=false
# Response: 404 - Note not found
```

---

### Phase 2: High Priority Fixes (2.5 hours)

#### Fix #2: Add User Ownership Validation (5 endpoints)
**File:** `app/api/notes.py`  
**Affected Lines:** 43 (list_notes), 51 (get_note), 60 (update_note), 130 (ask_ai), 148 (restore_note)  
**Change Type:** Add user validation  

**Endpoint: list_notes (line 43)**
```python
# ❌ BEFORE
@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(user_id: str, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """GET /: Returns all non-deleted notes for the user (paginated)."""
    return db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).offset(skip).limit(limit).all()

# ✅ AFTER
@router.get("", response_model=List[note_schema.NoteResponse])
@limiter.limit("60/minute")
def list_notes(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),  # ✅ Pagination validation
    db: Session = Depends(get_db)
):
    """GET /: Returns all non-deleted notes for the user (paginated)."""
    
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return db.query(models.Note).filter(
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).offset(skip).limit(limit).all()
```

**Endpoint: get_note (line 51)**
```python
# ❌ BEFORE - SECURITY ISSUE: Missing user_id param!
@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(note_id: str, db: Session = Depends(get_db)):
    """GET /{note_id}: Returns full note detail."""
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

# ✅ AFTER
@router.get("/{note_id}", response_model=note_schema.NoteResponse)
def get_note(note_id: str, user_id: str, db: Session = Depends(get_db)):
    """GET /{note_id}: Returns full note detail."""
    
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Verify ownership
    note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    return note
```

**Endpoint: update_note (line 60) - MAJOR CHANGES**
```python
# ❌ BEFORE
@router.patch("/{note_id}")
async def update_note(note_id: str, update_data: note_schema.NoteUpdate, db: Session = Depends(get_db)):
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    data = update_data.model_dump(exclude_unset=True)

    # Logic: Prevent archiving if Note has HIGH priority tasks that are not DONE
    if data.get("is_archived") is True:
        high_priority_tasks = db.query(models.Task).filter(
            models.Task.note_id == note_id,
            models.Task.priority == models.Priority.HIGH,
            models.Task.is_done == False,
            models.Task.is_deleted == False
        ).first()
        
        if high_priority_tasks:
            raise HTTPException(
                status_code=400, 
                detail="Cannot archive note: It contains unfinished HIGH priority tasks."
            )

    for key, value in data.items():
        setattr(db_note, key, value)
    
    db.commit()
    return {"message": "Update successful", "note": db_note}

# ✅ AFTER
@router.patch("/{note_id}")
async def update_note(
    note_id: str,
    user_id: str,  # ✅ Add user validation
    update_data: note_schema.NoteUpdate,
    db: Session = Depends(get_db)
):
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Verify ownership
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    data = update_data.model_dump(exclude_unset=True)

    # ✅ Enhanced archive validation
    if data.get("is_archived") is True:
        # Check if already archived
        if db_note.is_archived:
            raise HTTPException(status_code=400, detail="Note is already archived")
        
        # Prevent archiving if has any active tasks
        active_tasks = db.query(models.Task).filter(
            models.Task.note_id == note_id,
            models.Task.is_done == False,
            models.Task.is_deleted == False
        ).first()
        
        if active_tasks:
            raise HTTPException(
                status_code=400,
                detail="Cannot archive: Note has active tasks. Complete or delete them first."
            )
    
    # ✅ Always update timestamp
    db_note.updated_at = int(time.time() * 1000)

    for key, value in data.items():
        if key not in ["id", "user_id", "timestamp", "created_by"]:  # ✅ Protect these fields
            setattr(db_note, key, value)
    
    db.commit()
    return note_schema.NoteResponse.model_validate(db_note)  # ✅ Return schema
```

**Endpoint: ask_ai (line 130) - MAJOR CHANGES**
```python
# ❌ BEFORE
@router.post("/{note_id}/ask")
@limiter.limit("5/minute")
async def ask_ai(note_id: str, question: str, user_id: str, db: Session = Depends(get_db)):
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=403, detail="Access denied or note deleted.")
        
    answer = await ai_service.llm_brain(transcript=db_note.transcript_deepgram, question=question)
    return {"answer": answer}

# ✅ AFTER
@router.post("/{note_id}/ask")
@limiter.limit("20/minute")
async def ask_ai(
    note_id: str,
    question: str = Query(..., min_length=5, max_length=500),  # ✅ Validate
    user_id: str = Query(..., min_length=1),  # ✅ Validate
    db: Session = Depends(get_db)
):
    """POST /{note_id}/ask: Ask AI a question about the note."""
    
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Verify ownership
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=403, detail="Note not found or access denied")
    
    # ✅ Validate transcript exists
    if not db_note.transcript_deepgram or not db_note.transcript_deepgram.strip():
        raise HTTPException(status_code=400, detail="Note has no transcript for analysis")
    
    try:
        # ✅ Error handling
        answer = await ai_service.llm_brain(
            transcript=db_note.transcript_deepgram,
            question=question
        )
        
        if not answer:
            raise HTTPException(status_code=500, detail="Failed to generate answer")
        
        return {"answer": answer, "question": question}
        
    except TimeoutError:
        raise HTTPException(status_code=504, detail="AI service timeout - please try again")
    except Exception as e:
        print(f"AI service error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI service error - please try again")
```

**Endpoint: restore_note (line 148)**
```python
# ❌ BEFORE
@router.patch("/{note_id}/restore")
def restore_note(note_id: str, db: Session = Depends(get_db)):
    """PATCH: Restore a soft-deleted note and all its associated tasks."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    db_note.is_deleted = False
    db_note.deleted_at = None
    
    db.query(models.Task).filter(models.Task.note_id == note_id).update({
        "is_deleted": False, 
        "deleted_at": None
    })
    
    db.commit()
    return {"message": "Note and its tasks have been successfully restored."}

# ✅ AFTER
@router.patch("/{note_id}/restore")
def restore_note(note_id: str, user_id: str, db: Session = Depends(get_db)):
    """PATCH /{note_id}/restore: Restore a soft-deleted note."""
    
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Verify ownership and deletion status
    db_note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == True  # ✅ Only restore deleted notes
    ).first()
    
    if not db_note:
        raise HTTPException(status_code=404, detail="Deleted note not found")
    
    # ✅ Restore note with timestamp
    now = int(time.time() * 1000)
    db_note.is_deleted = False
    db_note.deleted_at = None
    db_note.updated_at = now
    
    # ✅ Restore all tasks with timestamp
    db.query(models.Task).filter(models.Task.note_id == note_id).update({
        "is_deleted": False,
        "deleted_at": None,
        "updated_at": now
    })
    
    db.commit()
    return {"message": "Note and its tasks restored successfully"}
```

**Update imports:**
```python
# ✅ Add Query import for validation
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Query
```

---

#### Fix #3: Add NoteUpdate Schema
**File:** `app/schemas/note.py`  
**Change Type:** Add new schema  

```python
# ✅ Add this class to schemas/note.py

class NoteUpdate(BaseModel):
    """Schema for updating note fields."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=1000)
    priority: Optional[Priority] = None
    status: Optional[NoteStatus] = None
    is_pinned: Optional[bool] = None
    is_liked: Optional[bool] = None
    is_archived: Optional[bool] = None
    document_urls: Optional[List[str]] = None
    links: Optional[List[ExternalLink]] = None
    # Note: These fields are NOT updatable
    # - id: Generated, immutable
    # - user_id: Set on creation
    # - timestamp: Creation time
    # - transcript_*: Set by AI processing
    # - updated_at: Auto-managed
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Updated Note Title",
                "summary": "Updated summary",
                "priority": "HIGH",
                "is_pinned": True,
                "is_archived": False
            }
        }
    )
```

---

#### Fix #4: Expand NoteResponse Schema
**File:** `app/schemas/note.py`  
**Change Type:** Add fields  

```python
# ❌ BEFORE
class NoteResponse(NoteBase):
    id: str
    timestamp: int
    transcript: str
    audio_url: Optional[str]
    tasks: List[TaskResponse]
    is_pinned: bool
    is_liked: bool
    is_archived: bool
    model_config = ConfigDict(from_attributes=True)

# ✅ AFTER
class NoteResponse(NoteBase):
    id: str
    user_id: str  # ✅ Add
    timestamp: int
    updated_at: int  # ✅ Add
    transcript: str
    audio_url: Optional[str]
    tasks: List[TaskResponse]
    is_pinned: bool
    is_liked: bool
    is_archived: bool
    is_deleted: bool  # ✅ Add
    deleted_at: Optional[int]  # ✅ Add
    model_config = ConfigDict(from_attributes=True)

class NoteDeleteResponse(BaseModel):  # ✅ Add new schema
    """Response for delete operations."""
    message: str
    type: str  # "soft" or "hard"
```

---

#### Fix #5: Add Timestamp Fields to Model
**File:** `app/db/models.py`  
**Change Type:** Add columns  

```python
# ❌ BEFORE
class Note(Base):
    __tablename__ = "notes"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    # ... other fields ...
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000))
    # ❌ No updated_at field
    # ❌ No created_by field

# ✅ AFTER
class Note(Base):
    __tablename__ = "notes"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    # ... other fields ...
    timestamp = Column(BigInteger, default=lambda: int(time.time() * 1000))
    updated_at = Column(BigInteger, default=lambda: int(time.time() * 1000))  # ✅ Add
    created_by = Column(String, ForeignKey("users.id"), nullable=True)  # ✅ Optional
    # ... rest of fields ...
```

---

#### Fix #6: Add Input Validation to process_note
**File:** `app/api/notes.py`  
**Lines:** 21-38  
**Change Type:** Add validation  

```python
# ❌ BEFORE
@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def process_note(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    instruction: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """POST /process: Main Upload for audio processing."""
    note_id = str(uuid.uuid4())
    temp_path = f"uploads/{note_id}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())

    process_audio_pipeline.delay(note_id, temp_path, user_id, instruction)
    
    return {"note_id": note_id, "message": "Processing started in background"}

# ✅ AFTER
@router.post("/process", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
async def process_note(
    file: UploadFile = File(...),
    user_id: str = Form(..., min_length=1),  # ✅ Validate not empty
    instruction: Optional[str] = Form(None, max_length=1000),  # ✅ Max length
    db: Session = Depends(get_db)
):
    """POST /process: Main upload for audio processing."""
    
    # ✅ Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # ✅ Validate file
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 50MB)")
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    
    # ✅ Validate file extension
    ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {file_ext}")
    
    note_id = str(uuid.uuid4())
    temp_path = f"uploads/{note_id}_{file.filename}"
    
    with open(temp_path, "wb") as buffer:
        buffer.write(content)

    process_audio_pipeline.delay(note_id, temp_path, user_id, instruction)
    
    return {
        "note_id": note_id,
        "message": "Processing started in background",
        "status": "processing"
    }
```

**Add import at top:**
```python
from pathlib import Path  # ✅ Add this
```

---

### Phase 3: Medium Priority Fixes (1.5 hours)

#### Fix #7: Add Transcript Validation
**File:** `app/schemas/note.py`  
**Change Type:** Add field validation  

```python
# ❌ BEFORE
class NoteCreate(NoteBase):
    user_id: str
    transcript: str
    transcript_groq: str = ""
    transcript_deepgram: str = ""
    transcript_elevenlabs: str = ""
    transcript_android: str = ""
    # ... no validation

# ✅ AFTER
class NoteCreate(NoteBase):
    user_id: str = Field(..., min_length=1)  # ✅ Validate
    transcript: str = Field(..., min_length=1, max_length=100000)  # ✅ Validate
    transcript_groq: str = Field("", max_length=100000)  # ✅ Validate
    transcript_deepgram: str = Field("", max_length=100000)  # ✅ Validate
    transcript_elevenlabs: str = Field("", max_length=100000)  # ✅ Validate
    transcript_android: str = Field("", max_length=100000)  # ✅ Validate
    # ... rest of fields
```

---

#### Fix #8: Add Response Consistency (Return Schemas Instead of Dicts)
**File:** `app/api/notes.py`  
**Multiple Locations**  
**Change Type:** Replace dict returns with schema returns  

```python
# ✅ Update delete_note to return schema
return note_schema.NoteDeleteResponse(
    message=msg,
    type="hard" if hard else "soft"
)

# ✅ Update ask_ai to include metadata
return {"answer": answer, "question": question, "note_id": note_id}

# ✅ Update restore_note
return note_schema.NoteResponse.model_validate(db_note)
```

---

## Summary of All Changes

### Files Modified: 3

```
app/api/notes.py
  ✅ Remove duplicate delete_note route (merge functions)
  ✅ Add user validation to 5 endpoints (list, get, update, ask, restore)
  ✅ Add input validation to process_note
  ✅ Add timestamp updates to update_note and restore_note
  ✅ Add error handling to ask_ai
  ✅ Update imports (add Query, Path)
  ✅ Return proper schemas instead of dicts

app/schemas/note.py
  ✅ Add NoteUpdate schema with field validation
  ✅ Expand NoteResponse with 4 new fields
  ✅ Add NoteDeleteResponse schema
  ✅ Add validation to NoteCreate fields
  ✅ Add validation to transcript fields

app/db/models.py
  ✅ Add updated_at column to Note model
  ✅ Add created_by column to Note model (optional)
```

### Total Lines Added: ~200 lines
### Total Complexity: Medium
### Total Estimated Time: 4 hours

---

## Testing Checklist

### Unit Tests to Write
- [ ] test_list_notes_validates_user
- [ ] test_list_notes_pagination
- [ ] test_get_note_ownership_check
- [ ] test_update_note_timestamp
- [ ] test_update_note_archive_validation
- [ ] test_delete_note_soft
- [ ] test_delete_note_hard
- [ ] test_restore_note_verification
- [ ] test_ask_ai_transcript_validation
- [ ] test_process_note_file_validation

### Integration Tests to Write
- [ ] User → Note → Task → Ask AI workflow
- [ ] Delete → Restore → Verify workflow
- [ ] File upload → Processing workflow
- [ ] Archive → Task completion → Unarchive workflow

### Manual Tests
- [ ] Test all endpoints with Postman
- [ ] Test error messages are clear
- [ ] Test timestamps are auto-updated
- [ ] Test user ownership is enforced

---

## Deployment Checklist

### Database Changes
```sql
-- Add new columns to notes table
ALTER TABLE notes ADD COLUMN updated_at BIGINT DEFAULT 0;
ALTER TABLE notes ADD COLUMN created_by VARCHAR;
-- Add index for performance
CREATE INDEX idx_notes_updated_at ON notes(updated_at);
```

### Code Changes
- [ ] All imports updated (Query, Path)
- [ ] All new schemas created
- [ ] All endpoints updated
- [ ] No syntax errors
- [ ] Type hints complete

### Testing
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Manual testing done
- [ ] Performance acceptable

### Documentation
- [ ] API documentation updated
- [ ] Error messages documented
- [ ] Examples provided

---

## Success Criteria

✅ **Functionality**
- All 8 endpoints working correctly
- User ownership enforced on all endpoints
- Input validation on all parameters
- Proper error messages returned

✅ **Code Quality**
- Type hints: 100%
- Schemas used consistently
- No duplicate code
- Proper error handling

✅ **Security**
- User ownership verified
- Input sanitized
- No SQL injection possible
- File uploads validated

✅ **Performance**
- Pagination implemented
- Queries optimized
- Response times <100ms average
- No N+1 queries

---

**Status:** Ready for Implementation  
**Priority:** High  
**Effort:** 4 hours  
**Risk:** Low (well-defined changes, clear patterns)  
