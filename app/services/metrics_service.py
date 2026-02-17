"""
Real-time Metrics Service
Collects and aggregates real-time system metrics
"""

import time
from datetime import datetime
from typing import Dict

import redis
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import ai_config
from app.db.models import Folder, Note, Task, Team, Transaction, User, Wallet
from app.services.system_health_service import SystemHealthService
from app.utils.json_logger import JLogger
from app.worker.task import celery_app


class MetricsService:
    """Collect real-time metrics"""

    @staticmethod
    def get_realtime_metrics(db: Session) -> Dict:
        """Get real-time system metrics"""
        try:
            r = redis.from_url(ai_config.REDIS_URL)
            
            # Get current users online (from Redis)
            users_online = r.scard("users:online") or 0
            
            # Get API requests per minute (from Redis counter)
            api_rpm = int(r.get("metrics:api_rpm") or 0)
            
            # Get notes processing now (Celery active tasks)
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active()
            notes_processing = 0
            if active_tasks:
                for worker_tasks in active_tasks.values():
                    notes_processing += sum(
                        1 for task in worker_tasks 
                        if task["name"] == "note_process_pipeline"
                    )
            
            # Get error rate (from Redis)
            total_requests = int(r.get("metrics:total_requests") or 1)
            error_requests = int(r.get("metrics:error_requests") or 0)
            error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Get average response time (from Redis)
            avg_response_time = float(r.get("metrics:avg_response_time") or 0)
            
            # Get Celery queue length
            reserved = inspect.reserved()
            queue_length = sum(len(tasks) for tasks in reserved.values()) if reserved else 0
            
            # Get Redis memory
            redis_info = r.info()
            redis_memory = round(redis_info["used_memory"] / 1024 / 1024, 2)
            
            # Get database connections (from pg_stat_activity - PostgreSQL only)
            db_connections = 0
            try:
                db_connections = db.execute(
                    text("SELECT count(*) FROM pg_stat_activity")
                ).scalar()
            except Exception:
                # Fallback for SQLite or if pg_stat_activity not available
                # Use active users in last 5 minutes as proxy for "online" users if DB connections can't be determined
                five_min_ago = int((time.time() - 5 * 60) * 1000)
                db_connections = db.query(User).filter(
                    User.last_login >= five_min_ago
                ).count()
            
            return {
                "current_users_online": int(users_online),
                "api_requests_per_minute": api_rpm,
                "notes_processing_now": notes_processing,
                "error_rate_percent": round(error_rate, 2),
                "avg_response_time_ms": round(avg_response_time, 2),
                "celery_queue_length": queue_length,
                "redis_memory_mb": redis_memory,
                "database_connections": db_connections,
                "timestamp": int(time.time() * 1000)
            }
        except Exception as e:
            JLogger.error("Failed to get realtime metrics", error=str(e))
            return {
                "error": str(e),
                "timestamp": int(time.time() * 1000)
            }

    @staticmethod
    def get_dashboard_overview(db: Session) -> Dict:
        """Get dashboard overview metrics"""
        try:
            # User metrics
            total_users = db.query(User).filter(User.is_deleted == False).count()
            active_users = db.query(User).filter(
                User.is_deleted == False,
                User.last_login >= int((time.time() - 30 * 24 * 60 * 60) * 1000)
            ).count()
            
            # Get new users this month
            month_start = int(datetime.now().replace(day=1, hour=0, minute=0, second=0).timestamp() * 1000)
            new_users = db.query(User).filter(
                User.last_login >= month_start
            ).count()
            
            deleted_users = db.query(User).filter(User.is_deleted == True).count()
            admin_count = db.query(User).filter(User.is_admin == True).count()
            
            # Content metrics
            total_notes = db.query(Note).filter(Note.is_deleted == False).count()
            total_tasks = db.query(Task).filter(Task.is_deleted == False).count()
            total_teams = db.query(Team).count()
            total_folders = db.query(Folder).count()
            
            # Activity today
            today_start = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp() * 1000)
            notes_today = db.query(Note).filter(Note.timestamp >= today_start).count()
            tasks_today = db.query(Task).filter(Task.created_at >= today_start).count()
            
            # New users (last 24h) - using last_login as proxy
            yesterday = int((time.time() - 86400) * 1000)
            new_users = db.query(User).filter(
                User.last_login >= yesterday
            ).count()
            
            # Active users last 24h
            day_ago = int((time.time() - 24 * 60 * 60) * 1000)
            active_24h = db.query(User).filter(User.last_login >= day_ago).count()
            
            # System health
            health = SystemHealthService.get_overall_health()
            
            # Revenue
            total_balance = db.query(func.sum(Wallet.balance)).scalar() or 0
            revenue_this_month = db.query(func.sum(Transaction.amount)).filter(
                Transaction.created_at >= month_start,
                Transaction.type == "DEPOSIT"
            ).scalar() or 0
            
            return {
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "new_this_month": new_users,
                    "deleted": deleted_users,
                    "admins": admin_count
                },
                "content": {
                    "total_notes": total_notes,
                    "total_tasks": total_tasks,
                    "total_teams": total_teams,
                    "total_folders": total_folders
                },
                "activity": {
                    "notes_today": notes_today,
                    "tasks_today": tasks_today,
                    "active_users_24h": active_24h
                },
                "system": {
                    "database_status": health["components"]["database"]["status"],
                    "redis_status": health["components"]["redis"]["status"],
                    "celery_workers": health["components"]["celery"].get("active_workers", 0)
                },
                "revenue": {
                    "total_balance": int(total_balance),
                    "revenue_this_month": int(revenue_this_month)
                }
            }
        except Exception as e:
            JLogger.error("Failed to get dashboard overview", error=str(e))
            return {
                "error": str(e)
            }
