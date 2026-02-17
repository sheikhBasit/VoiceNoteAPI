"""
Admin User Management Service
Handles user search, detail view, tier management, and session control
"""

import time
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.db.models import Note, RefreshToken, Task, User
from app.utils.json_logger import JLogger


class AdminUserManagementService:
    """Service for admin user management operations"""

    # ============================================================================
    # USER SEARCH & FILTERING
    # ============================================================================

    @staticmethod
    def search_users(
        db: Session,
        query: Optional[str] = None,
        tier: Optional[str] = None,
        is_admin: Optional[bool] = None,
        is_deleted: Optional[bool] = False,
        limit: int = 20,
        skip: int = 0
    ) -> Dict:
        """
        Search and filter users
        
        Args:
            query: Search by name or email
            tier: Filter by subscription tier
            is_admin: Filter by admin status
            is_deleted: Filter by deleted status
            limit: Results per page
            skip: Results to skip
        """
        db_query = db.query(User)
        
        # Apply filters
        if query:
            search_pattern = f"%{query}%"
            db_query = db_query.filter(
                or_(
                    User.name.ilike(search_pattern),
                    User.email.ilike(search_pattern)
                )
            )
        
        if tier:
            db_query = db_query.filter(User.tier == tier)
        
        if is_admin is not None:
            db_query = db_query.filter(User.is_admin == is_admin)
        
        if is_deleted is not None:
            db_query = db_query.filter(User.is_deleted == is_deleted)
        
        # Get total count
        total = db_query.count()
        
        # Apply pagination
        users = db_query.offset(skip).limit(limit).all()
        
        return {
            "users": users,
            "total": total,
            "limit": limit,
            "skip": skip
        }

    # ============================================================================
    # USER DETAIL VIEW
    # ============================================================================

    @staticmethod
    def get_user_detail(db: Session, user_id: str) -> Dict:
        """Get detailed user information"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise ValueError("User not found")
        
        # Get user statistics
        note_count = db.query(Note).filter(
            Note.user_id == user_id,
            Note.is_deleted == False
        ).count()
        
        task_count = db.query(Task).filter(
            Task.user_id == user_id,
            Task.is_deleted == False
        ).count()
        
        # Get active sessions
        active_sessions = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).count()
        
        return {
            "user": user,
            "statistics": {
                "note_count": note_count,
                "task_count": task_count,
                "active_sessions": active_sessions
            }
        }

    # ============================================================================
    # TIER MANAGEMENT
    # ============================================================================

    @staticmethod
    def update_user_tier(
        db: Session,
        user_id: str,
        new_tier: str,
        admin_id: str
    ) -> Dict:
        """Update user's subscription tier"""
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise ValueError("User not found")
        
        old_tier = user.tier
        user.tier = new_tier
        user.updated_at = int(time.time() * 1000)
        
        db.commit()
        
        JLogger.info(
            "User tier updated",
            user_id=user_id,
            old_tier=old_tier.name,
            new_tier=new_tier,
            admin_id=admin_id
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "old_tier": old_tier.name,
            "new_tier": new_tier
        }

    # ============================================================================
    # SESSION MANAGEMENT
    # ============================================================================

    @staticmethod
    def get_user_sessions(db: Session, user_id: str) -> Dict:
        """Get all active sessions for a user"""
        sessions = db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False
        ).all()
        
        session_list = []
        for session in sessions:
            session_list.append({
                "token_id": session.id,
                "device_id": session.device_id,
                "created_at": session.created_at,
                "expires_at": session.expires_at
            })
        
        return {
            "sessions": session_list,
            "total": len(session_list)
        }

    @staticmethod
    def force_logout(
        db: Session,
        user_id: str,
        admin_id: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Force logout user by revoking refresh tokens
        
        Args:
            user_id: User to logout
            admin_id: Admin performing action
            session_id: Optional specific session to revoke (all if None)
        """
        if session_id:
            # Revoke specific session
            session = db.query(RefreshToken).filter(
                RefreshToken.id == session_id,
                RefreshToken.user_id == user_id
            ).first()
            
            if not session:
                raise ValueError("Session not found")
            
            session.is_revoked = True
            revoked_count = 1
        else:
            # Revoke all sessions
            revoked_count = db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            ).update(
                {"is_revoked": True},
                synchronize_session=False
            )
        
        db.commit()
        
        JLogger.info(
            "User force logged out",
            user_id=user_id,
            admin_id=admin_id,
            sessions_revoked=revoked_count
        )
        
        return {
            "status": "success",
            "user_id": user_id,
            "sessions_revoked": revoked_count
        }

    # ============================================================================
    # USER ACTIVITY
    # ============================================================================

    @staticmethod
    def get_user_activity(
        db: Session,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """Get user activity for the last N days"""
        start_date = int((time.time() - days * 24 * 60 * 60) * 1000)
        
        # Notes created
        notes = db.query(Note).filter(
            Note.user_id == user_id,
            Note.timestamp >= start_date
        ).count()
        
        # Tasks created
        tasks = db.query(Task).filter(
            Task.user_id == user_id,
            Task.created_at >= start_date
        ).count()
        
        return {
            "user_id": user_id,
            "period_days": days,
            "notes_created": notes,
            "tasks_created": tasks,
            "total_actions": notes + tasks
        }
