"""
Admin Audit Service
Handles audit logs, activity tracking, and admin action monitoring
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.db.models import AdminActionLog, User
from app.utils.json_logger import JLogger


class AdminAuditService:
    """Service for admin audit logs and activity tracking"""

    # ============================================================================
    # AUDIT LOGS
    # ============================================================================

    @staticmethod
    def get_audit_logs(
        db: Session,
        admin_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
        skip: int = 0
    ) -> Dict:
        """
        Get audit logs with filtering
        
        Args:
            admin_id: Filter by admin user ID
            action: Filter by action type
            limit: Results per page
            skip: Results to skip
        """
        query = db.query(AdminActionLog)
        
        if admin_id:
            query = query.filter(AdminActionLog.admin_id == admin_id)
        
        if action:
            query = query.filter(AdminActionLog.action == action)
        
        # Order by most recent first
        query = query.order_by(desc(AdminActionLog.timestamp))
        
        total = query.count()
        logs = query.offset(skip).limit(limit).all()
        
        # Enrich with admin user info
        log_list = []
        for log in logs:
            admin_user = db.query(User).filter(User.id == log.admin_id).first()
            log_list.append({
                "id": log.id,
                "admin_id": log.admin_id,
                "admin_email": admin_user.email if admin_user else None,
                "admin_name": admin_user.name if admin_user else None,
                "action": log.action,
                "target_id": log.target_id,
                "details": log.details,
                "timestamp": log.timestamp,
                "timestamp_readable": datetime.fromtimestamp(log.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return {
            "logs": log_list,
            "total": total,
            "limit": limit,
            "skip": skip
        }

    @staticmethod
    def get_recent_activity(db: Session, hours: int = 24, limit: int = 20) -> Dict:
        """
        Get recent admin activity for dashboard
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of activities to return
        """
        cutoff_time = int((time.time() - hours * 60 * 60) * 1000)
        
        logs = db.query(AdminActionLog).filter(
            AdminActionLog.timestamp >= cutoff_time
        ).order_by(desc(AdminActionLog.timestamp)).limit(limit).all()
        
        activity_list = []
        for log in logs:
            admin_user = db.query(User).filter(User.id == log.admin_id).first()
            
            # Create human-readable activity message
            activity_msg = AdminAuditService._format_activity_message(log, admin_user)
            
            activity_list.append({
                "id": log.id,
                "message": activity_msg,
                "action": log.action,
                "admin_name": admin_user.name if admin_user else "Unknown Admin",
                "timestamp": log.timestamp,
                "time_ago": AdminAuditService._time_ago(log.timestamp)
            })
        
        return {
            "recent_activity": activity_list,
            "period_hours": hours,
            "count": len(activity_list)
        }

    @staticmethod
    def get_admin_action_stats(db: Session, days: int = 30) -> Dict:
        """
        Get statistics on admin actions
        
        Args:
            days: Number of days to analyze
        """
        cutoff_time = int((time.time() - days * 24 * 60 * 60) * 1000)
        
        # Get all logs in period
        logs = db.query(AdminActionLog).filter(
            AdminActionLog.timestamp >= cutoff_time
        ).all()
        
        # Count by action type
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        # Count by admin
        admin_counts = {}
        for log in logs:
            admin_counts[log.admin_id] = admin_counts.get(log.admin_id, 0) + 1
        
        # Get top admins
        top_admins = []
        for admin_id, count in sorted(admin_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            admin_user = db.query(User).filter(User.id == admin_id).first()
            top_admins.append({
                "admin_id": admin_id,
                "admin_name": admin_user.name if admin_user else "Unknown",
                "admin_email": admin_user.email if admin_user else None,
                "action_count": count
            })
        
        # Actions by day
        actions_by_day = {}
        for log in logs:
            day = datetime.fromtimestamp(log.timestamp / 1000).strftime("%Y-%m-%d")
            actions_by_day[day] = actions_by_day.get(day, 0) + 1
        
        return {
            "total_actions": len(logs),
            "action_counts": action_counts,
            "top_admins": top_admins,
            "actions_by_day": actions_by_day,
            "period_days": days
        }

    @staticmethod
    def get_activity_timeline(db: Session, days: int = 7) -> Dict:
        """
        Get activity timeline for visualization
        
        Args:
            days: Number of days to include
        """
        cutoff_time = int((time.time() - days * 24 * 60 * 60) * 1000)
        
        logs = db.query(AdminActionLog).filter(
            AdminActionLog.timestamp >= cutoff_time
        ).order_by(AdminActionLog.timestamp).all()
        
        # Group by hour
        timeline = {}
        for log in logs:
            hour = datetime.fromtimestamp(log.timestamp / 1000).strftime("%Y-%m-%d %H:00")
            if hour not in timeline:
                timeline[hour] = {
                    "total": 0,
                    "actions": {}
                }
            timeline[hour]["total"] += 1
            timeline[hour]["actions"][log.action] = timeline[hour]["actions"].get(log.action, 0) + 1
        
        return {
            "timeline": timeline,
            "period_days": days
        }

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    @staticmethod
    def _format_activity_message(log: AdminActionLog, admin_user: Optional[User]) -> str:
        """Format activity log into human-readable message"""
        admin_name = admin_user.name if admin_user else "Admin"
        
        action_messages = {
            "VIEW_DASHBOARD": f"{admin_name} viewed the dashboard",
            "DELETE_TASK": f"{admin_name} deleted a task",
            "RESTORE_TASK": f"{admin_name} restored a task",
            "CREATE_TEST_NOTE": f"{admin_name} created a test note",
            "CREATE_API_KEY": f"{admin_name} created an API key",
            "UPDATE_API_KEY": f"{admin_name} updated an API key",
            "DELETE_API_KEY": f"{admin_name} deleted an API key",
            "BULK_DELETE": f"{admin_name} performed bulk delete",
            "BULK_RESTORE": f"{admin_name} performed bulk restore",
            "CREDIT_WALLET": f"{admin_name} credited a wallet",
            "DEBIT_WALLET": f"{admin_name} debited a wallet",
            "FREEZE_WALLET": f"{admin_name} froze a wallet",
            "UNFREEZE_WALLET": f"{admin_name} unfroze a wallet",
            "RETRY_CELERY_TASK": f"{admin_name} retried a Celery task",
            "CANCEL_CELERY_TASK": f"{admin_name} cancelled a Celery task",
            "SHUTDOWN_WORKER": f"{admin_name} shut down a worker",
            "RESTART_WORKER_POOL": f"{admin_name} restarted worker pool",
            "PURGE_QUEUE": f"{admin_name} purged a queue",
            "UPDATE_USER_TIER": f"{admin_name} updated user tier",
            "FORCE_LOGOUT": f"{admin_name} forced user logout",
        }
        
        return action_messages.get(log.action, f"{admin_name} performed {log.action}")

    @staticmethod
    def _time_ago(timestamp_ms: int) -> str:
        """Convert timestamp to human-readable 'time ago' format"""
        now = time.time() * 1000
        diff_ms = now - timestamp_ms
        diff_seconds = diff_ms / 1000
        
        if diff_seconds < 60:
            return "just now"
        elif diff_seconds < 3600:
            minutes = int(diff_seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff_seconds < 86400:
            hours = int(diff_seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(diff_seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
