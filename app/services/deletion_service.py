"""
Deletion Service - Professional Database Cascade Deletion

Handles soft delete, hard delete, and cascade deletion logic with audit logging.
Follows database engineering best practices for referential integrity.
"""

import os
import time
from typing import Any, Dict, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Note, Task, User
from app.utils.json_logger import JLogger


class DeletionService:
    """
    Professional deletion service with cascade logic and audit trails.

    Features:
    - Soft delete with cascade (restorable)
    - Hard delete with cascade (permanent, admin only)
    - Deletion audit logging
    - Referential integrity maintenance
    - Transaction management
    """

    @staticmethod
    def soft_delete_user(
        db: Session, user_id: str, deleted_by: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Soft delete user and cascade to all notes and tasks.

        Args:
            db: Database session
            user_id: User ID to delete
            deleted_by: User ID performing the deletion
            reason: Optional reason for deletion

        Returns:
            dict: Deletion summary with counts
        """
        JLogger.info(
            "Starting soft delete user", user_id=user_id, deleted_by=deleted_by
        )

        try:
            # Get user
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                JLogger.warning("User not found for deletion", user_id=user_id)
                return {"success": False, "error": "User not found"}

            if user.is_deleted:
                JLogger.warning("User already deleted", user_id=user_id)
                return {"success": False, "error": "User already deleted"}

            timestamp = int(time.time() * 1000)

            # Count items before deletion
            notes_count = (
                db.query(Note)
                .filter(and_(Note.user_id == user_id, Note.is_deleted == False))
                .count()
            )

            tasks_count = (
                db.query(Task)
                .filter(and_(Task.user_id == user_id, Task.is_deleted == False))
                .count()
            )

            # Soft delete all tasks first
            tasks = (
                db.query(Task)
                .filter(and_(Task.user_id == user_id, Task.is_deleted == False))
                .all()
            )

            for task in tasks:
                task.is_deleted = True
                task.deleted_at = timestamp
                task.deleted_by = deleted_by
                task.deletion_reason = f"Cascade from user deletion: {user_id}"
                task.can_restore = True

            # Soft delete all notes and their associated tasks
            notes = (
                db.query(Note)
                .filter(and_(Note.user_id == user_id, Note.is_deleted == False))
                .all()
            )

            for note in notes:
                # Cascade to tasks of this note
                tasks_of_note = (
                    db.query(Task)
                    .filter(and_(Task.note_id == note.id, Task.is_deleted == False))
                    .all()
                )
                for t in tasks_of_note:
                    if not t.is_deleted:
                        t.is_deleted = True
                        t.deleted_at = timestamp
                        t.deleted_by = deleted_by
                        t.deletion_reason = (
                            f"Cascade from note deletion (User cascade): {user_id}"
                        )
                        t.can_restore = True
                        tasks_count += 1

                note.is_deleted = True
                note.deleted_at = timestamp
                note.deleted_by = deleted_by
                note.deletion_reason = f"Cascade from user deletion: {user_id}"
                note.can_restore = True

            # Soft delete user
            user.is_deleted = True
            user.deleted_at = timestamp
            user.deleted_by = deleted_by
            user.deletion_reason = reason or "User requested deletion"
            user.can_restore = True

            db.commit()

            JLogger.info(
                "User soft deleted successfully",
                user_id=user_id,
                notes_deleted=notes_count,
                tasks_deleted=tasks_count,
            )

            return {
                "success": True,
                "user_id": user_id,
                "notes_deleted": notes_count,
                "tasks_deleted": tasks_count,
                "total_items": 1 + notes_count + tasks_count,
                "can_restore": True,
            }

        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during user soft delete", user_id=user_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def soft_delete_note(
        db: Session, note_id: str, deleted_by: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Soft delete note and cascade to all tasks.

        Args:
            db: Database session
            note_id: Note ID to delete
            deleted_by: User ID performing the deletion
            reason: Optional reason for deletion

        Returns:
            dict: Deletion summary with counts
        """
        JLogger.info(
            "Starting soft delete note", note_id=note_id, deleted_by=deleted_by
        )

        try:
            # Get note
            note = db.query(Note).filter(Note.id == note_id).first()
            if not note:
                JLogger.warning("Note not found for deletion", note_id=note_id)
                return {"success": False, "error": "Note not found"}

            if note.is_deleted:
                JLogger.warning("Note already deleted", note_id=note_id)
                return {"success": False, "error": "Note already deleted"}

            timestamp = int(time.time() * 1000)

            # Count tasks before deletion
            tasks_count = (
                db.query(Task)
                .filter(and_(Task.note_id == note_id, Task.is_deleted == False))
                .count()
            )

            # Soft delete all tasks
            tasks = (
                db.query(Task)
                .filter(and_(Task.note_id == note_id, Task.is_deleted == False))
                .all()
            )

            for task in tasks:
                task.is_deleted = True
                task.deleted_at = timestamp
                task.deleted_by = deleted_by
                task.deletion_reason = f"Cascade from note deletion: {note_id}"
                task.can_restore = True

            # Soft delete note
            note.is_deleted = True
            note.deleted_at = timestamp
            note.deleted_by = deleted_by
            note.deletion_reason = reason or "Note deleted"
            note.can_restore = True

            db.commit()

            JLogger.info(
                "Note soft deleted successfully",
                note_id=note_id,
                tasks_deleted=tasks_count,
            )

            return {
                "success": True,
                "note_id": note_id,
                "tasks_deleted": tasks_count,
                "total_items": 1 + tasks_count,
                "can_restore": True,
            }

        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during note soft delete", note_id=note_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def soft_delete_task(
        db: Session, task_id: str, deleted_by: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Soft delete a single task.

        Args:
            db: Database session
            task_id: Task ID to delete
            deleted_by: User ID performing the deletion
            reason: Optional reason for deletion

        Returns:
            dict: Deletion summary
        """
        JLogger.info(
            "Starting soft delete task", task_id=task_id, deleted_by=deleted_by
        )

        try:
            # Get task
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                JLogger.warning("Task not found for deletion", task_id=task_id)
                return {"success": False, "error": "Task not found"}

            if task.is_deleted:
                JLogger.warning("Task already deleted", task_id=task_id)
                return {"success": False, "error": "Task already deleted"}

            timestamp = int(time.time() * 1000)

            # Soft delete task
            task.is_deleted = True
            task.deleted_at = timestamp
            task.deleted_by = deleted_by
            task.deletion_reason = reason or "Task deleted"
            task.can_restore = True

            db.commit()

            JLogger.info("Task soft deleted successfully", task_id=task_id)

            return {"success": True, "task_id": task_id, "can_restore": True}

        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during task soft delete", task_id=task_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def hard_delete_note(
        db: Session, note_id: str, admin_id: str = None
    ) -> Dict[str, Any]:
        """
        Permanently delete note and its audio file.
        """
        JLogger.info("Starting HARD DELETE note", note_id=note_id)

        try:
            note = db.query(Note).filter(Note.id == note_id).first()
            if not note:
                return {"success": False, "error": "Note not found"}

            # File Cleanup logic
            file_path = None
            # Standard logic: raw_audio_url = "uploads/xyz"
            if note.raw_audio_url and (
                note.raw_audio_url.startswith("uploads/")
                or note.raw_audio_url.startswith("/app/uploads/")
            ):
                file_path = note.raw_audio_url.replace(
                    "/app/", ""
                )  # Adjust for container path if needed

            # Safety check: Prevent deleting outside uploads
            if file_path and ".." not in file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    JLogger.info("Deleted audio file", path=file_path)
                except Exception as file_error:
                    JLogger.error(
                        "Failed to delete audio file",
                        path=file_path,
                        error=str(file_error),
                    )

            # Hard delete from DB
            db.delete(note)
            db.commit()

            JLogger.info("Note HARD DELETED successfully", note_id=note_id)
            return {"success": True, "note_id": note_id}

        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during note hard delete", note_id=note_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def restore_user(db: Session, user_id: str, restored_by: str) -> Dict[str, Any]:
        """
        Restore a soft-deleted user and optionally cascade restore.

        Args:
            db: Database session
            user_id: User ID to restore
            restored_by: User ID performing the restoration

        Returns:
            dict: Restoration summary
        """
        JLogger.info("Starting restore user", user_id=user_id, restored_by=restored_by)

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            if not user.is_deleted:
                return {"success": False, "error": "User is not deleted"}

            if not user.can_restore:
                return {"success": False, "error": "User cannot be restored"}

            # Restore user
            user.is_deleted = False
            user.deleted_at = None
            user.deleted_by = None
            user.deletion_reason = None

            # Count restored items
            notes_restored = 0
            tasks_restored = 0

            # Optionally restore notes (user choice)
            # For now, we'll restore all restorable items
            notes = (
                db.query(Note)
                .filter(
                    and_(
                        Note.user_id == user_id,
                        Note.is_deleted == True,
                        Note.can_restore == True,
                    )
                )
                .all()
            )

            for note in notes:
                note.is_deleted = False
                note.deleted_at = None
                note.deleted_by = None
                note.deletion_reason = None
                notes_restored += 1

                # Restore tasks for this note
                tasks = (
                    db.query(Task)
                    .filter(
                        and_(
                            Task.note_id == note.id,
                            Task.is_deleted == True,
                            Task.can_restore == True,
                        )
                    )
                    .all()
                )

                for task in tasks:
                    task.is_deleted = False
                    task.deleted_at = None
                    task.deleted_by = None
                    task.deletion_reason = None
                    tasks_restored += 1

            db.commit()

            JLogger.info(
                "User restored successfully",
                user_id=user_id,
                notes_restored=notes_restored,
                tasks_restored=tasks_restored,
            )

            return {
                "success": True,
                "user_id": user_id,
                "notes_restored": notes_restored,
                "tasks_restored": tasks_restored,
            }

        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during user restoration", user_id=user_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def restore_note(db: Session, note_id: str, restored_by: str) -> Dict[str, Any]:
        """
        Restore a soft-deleted note and its associated tasks.
        """
        JLogger.info("Starting restore note", note_id=note_id, restored_by=restored_by)
        try:
            note = db.query(Note).filter(Note.id == note_id).first()
            if not note:
                return {"success": False, "error": "Note not found"}
            if not note.is_deleted:
                return {"success": False, "error": "Note not deleted"}

            note.is_deleted = False
            note.deleted_at = None
            note.deleted_by = None
            note.deletion_reason = None

            # Restore tasks
            tasks = (
                db.query(Task)
                .filter(
                    and_(
                        Task.note_id == note_id,
                        Task.is_deleted == True,
                        Task.can_restore == True,
                    )
                )
                .all()
            )

            for task in tasks:
                task.is_deleted = False
                task.deleted_at = None
                task.deleted_by = None
                task.deletion_reason = None

            db.commit()
            return {"success": True, "note_id": note_id, "tasks_restored": len(tasks)}
        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during note restoration", note_id=note_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def restore_task(db: Session, task_id: str, restored_by: str) -> Dict[str, Any]:
        """
        Restore a soft-deleted task.
        """
        JLogger.info("Starting restore task", task_id=task_id, restored_by=restored_by)
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"success": False, "error": "Task not found"}
            if not task.is_deleted:
                return {"success": False, "error": "Task not deleted"}

            task.is_deleted = False
            task.deleted_at = None
            task.deleted_by = None
            task.deletion_reason = None

            db.commit()
            return {"success": True, "task_id": task_id}
        except Exception as e:
            db.rollback()
            JLogger.error(
                "Error during task restoration", task_id=task_id, error=str(e)
            )
            return {"success": False, "error": str(e)}

    @staticmethod
    def hard_delete_user(db: Session, user_id: str, admin_id: str) -> Dict[str, Any]:
        """
        Permanently delete user and all associated data (admin only).

        WARNING: This is irreversible!

        Args:
            db: Database session
            user_id: User ID to delete
            admin_id: Admin user ID performing the deletion

        Returns:
            dict: Deletion summary
        """
        JLogger.warning(
            "Starting HARD DELETE user (irreversible)",
            user_id=user_id,
            admin_id=admin_id,
        )

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return {"success": False, "error": "User not found"}

            # Count items
            notes_count = db.query(Note).filter(Note.user_id == user_id).count()
            tasks_count = db.query(Task).filter(Task.user_id == user_id).count()

            # Hard delete (CASCADE will handle notes and tasks)
            db.delete(user)
            db.commit()

            JLogger.warning(
                "User HARD DELETED permanently",
                user_id=user_id,
                admin_id=admin_id,
                notes_deleted=notes_count,
                tasks_deleted=tasks_count,
            )

            return {
                "success": True,
                "user_id": user_id,
                "notes_deleted": notes_count,
                "tasks_deleted": tasks_count,
                "permanent": True,
            }

        except Exception as e:
            db.rollback()
            JLogger.error("Error during hard delete", user_id=user_id, error=str(e))
            return {"success": False, "error": str(e)}
