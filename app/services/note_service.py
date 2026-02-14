import os
import time
import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.db import models
from app.schemas import note as note_schema
from app.utils.exceptions import NotFoundError, PermissionDeniedError, VoiceNoteError
from app.utils.json_logger import JLogger
from app.services.storage_service import StorageService
from app.services.analytics_service import AnalyticsService
from app.utils.security import verify_note_ownership
from app.worker.task import generate_note_embeddings_task, analyze_note_semantics_task, note_process_pipeline

class NoteService:
    @staticmethod
    def verify_note_access(db: Session, user: models.User, note_id: str) -> models.Note:
        """
        Verify if a user has access to a note (owner or team member).
        """
        note = db.query(models.Note).filter(models.Note.id == note_id).first()
        if not note:
            raise NotFoundError("Note", note_id)
        
        # Admin bypass
        if user.is_admin:
            return note
            
        # Ownership check
        if note.user_id == user.id:
            return note
            
        # Team check
        if note.team_id:
            is_member = db.query(models.Team).filter(
                models.Team.id == note.team_id,
                models.Team.members.any(id=user.id)
            ).first() or note.team.owner_id == user.id
            if is_member:
                return note
                
        raise PermissionDeniedError("You do not have permission to access this note")

    @classmethod
    def create_note_record(
        cls, 
        db: Session, 
        user: models.User, 
        data: Dict[str, Any],
        is_pending: bool = False
    ) -> models.Note:
        """
        Handles core note creation logic.
        """
        note_id = data.get("id") or str(uuid.uuid4())
        
        status = models.NoteStatus.PENDING if is_pending else models.NoteStatus.DONE
        
        db_note = models.Note(
            id=note_id,
            user_id=user.id,
            title=data.get("title") or "Untitled Note",
            summary=data.get("summary") or "",
            transcript_groq=data.get("transcript") or data.get("transcript_groq") or "",
            transcript_android=data.get("transcript_android") or "", # Fallback
            priority=data.get("priority") or models.Priority.MEDIUM,
            status=status,
            raw_audio_url=data.get("audio_url") or data.get("raw_audio_url"),
            languages=data.get("languages") or [],
            document_uris=data.get("document_uris") or [],
            image_uris=data.get("image_uris") or [],
            stt_model=data.get("stt_model") or "nova",
            team_id=data.get("team_id"),
            timestamp=int(time.time() * 1000),
            updated_at=int(time.time() * 1000),
        )
        
        db.add(db_note)
        db.commit()
        db.refresh(db_note)
        
        # Async hooks
        if db_note.team_id:
            from app.services.broadcaster import broadcaster
            # Note: broadcaster is usually async, but this is a sync service method
            # We will handle the async push in the API layer or using a background task helper
            pass
            
        if not is_pending:
            generate_note_embeddings_task.delay(note_id)
            if db_note.transcript_groq:
                analyze_note_semantics_task.delay(note_id)
                
        return db_note

    @classmethod
    def list_notes(
        cls, 
        db: Session, 
        user: models.User, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[models.Note]:
        """
        Retrieve paginated notes accessible to the user.
        """
        team_ids = [t.id for t in user.teams] + [t.id for t in user.owned_teams]
        
        return (
            db.query(models.Note)
            .options(joinedload(models.Note.tasks))
            .filter(
                models.Note.is_deleted == False,
                or_(
                    models.Note.user_id == user.id,
                    models.Note.team_id.in_(team_ids)
                )
            )
            .order_by(models.Note.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @classmethod
    def get_note(cls, db: Session, user: models.User, note_id: str, verbose: bool = False) -> models.Note:
        """
        Retrieves a note with related data and ownership check.
        """
        note = cls.verify_note_access(db, user, note_id)
        
        # Semantic linking
        if note.embedding is not None:
            team_ids = [t.id for t in user.teams] + [t.id for t in user.owned_teams]
            related = (
                db.query(models.Note)
                .filter(
                    models.Note.id != note_id,
                    models.Note.is_deleted == False,
                    or_(
                        models.Note.user_id == user.id,
                        models.Note.team_id.in_(team_ids)
                    )
                )
                .order_by(models.Note.embedding.cosine_distance(note.embedding))
                .limit(3)
                .all()
            )
            note.related_notes = related
        else:
            note.related_notes = []
            
        # Comparison toggle
        if not verbose:
            note.transcript_groq = None
            note.transcript_deepgram = None
            note.transcript_android = None
            
        return note

    @classmethod
    def update_note(cls, db: Session, user: models.User, note_id: str, data: Dict[str, Any]) -> models.Note:
        """
        Updates a note with business rule enforcement.
        """
        note = cls.verify_note_access(db, user, note_id)
        
        # 1. Enforcement: Prevent archive if high-prio tasks incomplete
        if data.get("is_archived") is True and not note.is_archived:
            cls._check_high_priority_tasks(db, note_id)
            
        # 2. Enforcement: Deletion checks
        if "is_deleted" in data:
            if data["is_deleted"]:
                cls._check_high_priority_tasks(db, note_id)
                # Delegate to actual delete logic
                from app.services.deletion_service import DeletionService
                DeletionService.soft_delete_note(db, note_id, deleted_by=user.id)
                db.refresh(note)
                return note
            else:
                from app.services.deletion_service import DeletionService
                DeletionService.restore_note(db, note_id, restored_by=user.id)
                db.refresh(note)
                return note

        # 3. Update fields
        for key, value in data.items():
            setattr(note, key, value)
            
        if any(k in data for k in ["title", "summary"]):
            generate_note_embeddings_task.delay(note_id)
            
        note.updated_at = int(time.time() * 1000)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def _check_high_priority_tasks(db: Session, note_id: str):
        high_prio = db.query(models.Task).filter(
            models.Task.note_id == note_id,
            models.Task.priority == models.Priority.HIGH,
            models.Task.is_done == False,
            models.Task.is_deleted == False
        ).first()
        if high_prio:
            raise VoiceNoteError(
                "Action restricted: Note has incomplete high-priority tasks.",
                code="TASK_CONSTRAINT",
                status_code=400
            )

    @classmethod
    def soft_delete_note(cls, db: Session, user: models.User, note_id: str):
        """
        Soft delete a note and its associated tasks.
        """
        note = cls.verify_note_access(db, user, note_id)
        
        # Enforce business rule: Cannot delete if high-priority tasks are pending
        cls._check_high_priority_tasks(db, note_id)
        
        note.is_deleted = True
        note.deleted_at = int(time.time() * 1000)
        note.deleted_by = user.id
        
        # Cascade to tasks
        db.query(models.Task).filter(models.Task.note_id == note_id).update({
            "is_deleted": True,
            "deleted_at": int(time.time() * 1000),
            "deleted_by": user.id
        })
        
        db.commit()
        JLogger.info("Note soft-deleted", note_id=note_id, user_id=user.id)

    @classmethod
    def restore_note(cls, db: Session, user: models.User, note_id: str):
        """
        Restore a soft-deleted note.
        """
        note = db.query(models.Note).filter(models.Note.id == note_id).first()
        if not note:
            raise NotFoundError("Note", note_id)
            
        # Permission check
        if note.user_id != user.id and not user.is_admin:
            raise PermissionDeniedError("Only the owner can restore a note")
            
        note.is_deleted = False
        note.deleted_at = None
        
        # Restore tasks
        db.query(models.Task).filter(models.Task.note_id == note_id).update({
            "is_deleted": False,
            "deleted_at": None
        })
        
        db.commit()
        JLogger.info("Note restored", note_id=note_id, user_id=user.id)

    @classmethod
    async def process_note_upload(
        cls,
        db: Session,
        user: models.User,
        file: Optional[Any],
        storage_key: Optional[str],
        note_id_override: Optional[str],
        mode: str,
        languages: Optional[str],
        stt_model: str,
        document_uris: Optional[str],
        image_uris: Optional[str],
        team_id: Optional[str],
        debug_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Comprehensive handler for note audio upload and processing.
        """
        note_id = note_id_override if note_id_override else str(uuid.uuid4())
        temp_path = None
        
        # 1. Handle File Upload if present
        if file:
            if not os.path.exists("uploads"):
                os.makedirs("uploads")
            temp_path = f"uploads/{note_id}_{file.filename}"
            total_size = 0
            MAX_FILE_SIZE = 50 * 1024 * 1024
            
            with open(temp_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):
                    total_size += len(chunk)
                    if total_size > MAX_FILE_SIZE:
                        os.remove(temp_path)
                        raise VoiceNoteError("File too large", code="FILE_TOO_LARGE", status_code=413)
                    buffer.write(chunk)
        elif not storage_key:
            raise VoiceNoteError("Missing audio sources", code="MISSING_SOURCE", status_code=400)
            
        # 2. Parse metadata
        doc_uri_list = [d.strip() for d in document_uris.split(",")] if document_uris else []
        img_uri_list = [i.strip() for i in image_uris.split(",")] if image_uris else []
        lang_list = [l.strip() for l in languages.split(",")] if languages else user.preferred_languages
        
        # 3. Create Note Record
        note_data = {
            "id": note_id,
            "title": f"Processing: {file.filename if file else 'Storage Key Extraction'}",
            "audio_url": storage_key if storage_key else temp_path,
            "languages": lang_list,
            "document_uris": doc_uri_list,
            "image_uris": img_uri_list,
            "stt_model": stt_model,
            "team_id": team_id
        }
        
        db_note = cls.create_note_record(db, user, note_data, is_pending=True)
        
        # 4. Trigger Broadcasting (Async helper should be used here)
        if team_id:
            from app.services.broadcaster import broadcaster
            await broadcaster.push_team_event(
                team_id,
                "NOTE_CREATED",
                {"note_id": note_id, "status": "PENDING", "user_id": user.id},
            )
            
        # 5. Pipeline Trigger
        trigger_path = temp_path if temp_path else storage_key
        if debug_sync:
            result = note_process_pipeline(
                note_id, trigger_path, mode, doc_uri_list, img_uri_list, lang_list, stt_model
            )
            return {"note_id": note_id, "message": "Sync complete", "result": result}
            
        note_process_pipeline.delay(
            note_id, trigger_path, mode, doc_uri_list, img_uri_list, lang_list, stt_model
        )
        
        return {"note_id": note_id, "message": f"Processing started in {mode} mode"}

    @classmethod
    def get_dashboard_metrics(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """
        Calculates productivity metrics for the user dashboard.
        """
        try:
            analytics = AnalyticsService()
            return analytics.get_productivity_pulse(db, user_id)
        except Exception as e:
            JLogger.error("Dashboard metrics failed", user_id=user_id, error=str(e))
            raise VoiceNoteError("Failed to load dashboard metrics", status_code=500)

    @classmethod
    def search_autocomplete(cls, db: Session, user: models.User, query_str: str) -> List[str]:
        """
        Suggests terms for search based on note titles.
        """
        team_ids = [t.id for t in user.teams] + [t.id for t in user.owned_teams]
        titles = (
            db.query(models.Note.title)
            .filter(
                models.Note.is_deleted == False,
                models.Note.title.ilike(f"%{query_str}%"),
                or_(
                    models.Note.user_id == user.id,
                    models.Note.team_id.in_(team_ids)
                )
            )
            .limit(10)
            .all()
        )
        return [t[0] for t in titles]

    @classmethod
    def bulk_move_notes(cls, db: Session, user: models.User, note_ids: List[str], folder_id: Optional[str]):
        """
        Moves multiple notes to a folder.
        """
        if folder_id:
            folder = db.query(models.Folder).filter(
                models.Folder.id == folder_id, 
                models.Folder.user_id == user.id
            ).first()
            if not folder:
                raise NotFoundError("Folder", folder_id)
                
        updated_count = (
            db.query(models.Note)
            .filter(
                models.Note.id.in_(note_ids), 
                models.Note.user_id == user.id
            )
            .update({models.Note.folder_id: folder_id}, synchronize_session=False)
        )
        db.commit()
        return {"message": f"Moved {updated_count} notes successfully"}

    @classmethod
    def hard_delete_note(cls, db: Session, user: models.User, note_id: str) -> Dict[str, Any]:
        """
        Permanently deletes a note and its storage files.
        """
        cls.verify_note_access(db, user, note_id)
        from app.services.deletion_service import DeletionService
        return DeletionService.hard_delete_note(db, note_id)

    @classmethod
    def bulk_delete_notes(cls, db: Session, user: models.User, note_ids: List[str], hard: bool = False):
        """
        Batch deletion of notes with constraint checking.
        """
        deleted_count = 0
        errors = []
        
        for nid in note_ids:
            try:
                if hard:
                    from app.services.deletion_service import DeletionService
                    cls.verify_note_access(db, user, nid) # Ownership check
                    res = DeletionService.hard_delete_note(db, nid)
                    if res["success"]:
                        deleted_count += 1
                else:
                    cls.soft_delete_note(db, user, nid)
                    deleted_count += 1
            except VoiceNoteError as ve:
                errors.append(f"Note {nid}: {ve.message}")
            except Exception as e:
                errors.append(f"Note {nid}: Unexpected error {str(e)}")
                
        return {
            "message": f"Bulk delete completed. Deleted {deleted_count}/{len(note_ids)} notes.",
            "deleted_count": deleted_count,
            "errors": errors
        }

    @classmethod
    def trigger_semantic_analysis(cls, db: Session, user: models.User, note_id: str):
        """
        Manually trigger semantic analysis for a note.
        """
        cls.verify_note_access(db, user, note_id)
        from app.worker.task import analyze_note_semantics_task
        analyze_note_semantics_task.delay(note_id)
        return {"message": "Semantic analysis queued", "note_id": note_id}
