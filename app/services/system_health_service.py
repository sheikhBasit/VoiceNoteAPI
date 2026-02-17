"""
System Health Monitoring Service
Checks database, Redis, Celery, and disk health
"""

import time
from typing import Dict

import psutil
import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import ai_config
from app.db.session import SessionLocal
from app.utils.json_logger import JLogger
from app.worker.task import celery_app


class SystemHealthService:
    """Monitor system component health"""

    @staticmethod
    def check_database_health(db: Session) -> Dict:
        """Check PostgreSQL database health"""
        try:
            start_time = time.time()
            db.execute(text("SELECT 1"))
            response_time = (time.time() - start_time) * 1000
            
            # Get connection pool stats
            pool = db.get_bind().pool
            pool_size = pool.size()
            pool_checked_out = pool.checkedout()
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "connection_pool": f"{pool_checked_out}/{pool_size}",
                "pool_overflow": pool.overflow()
            }
        except Exception as e:
            JLogger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_redis_health() -> Dict:
        """Check Redis health"""
        try:
            r = redis.from_url(ai_config.REDIS_URL)
            start_time = time.time()
            r.ping()
            response_time = (time.time() - start_time) * 1000
            
            info = r.info()
            
            # Calculate hit rate safely
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            hit_rate = round(hits / (hits + misses) * 100, 2) if (hits + misses) > 0 else 0
            
            return {
                "status": "healthy",
                "response_time_ms": round(response_time, 2),
                "memory_used_mb": round(info["used_memory"] / 1024 / 1024, 2),
                "connected_clients": info["connected_clients"],
                "uptime_seconds": info["uptime_in_seconds"],
                "hit_rate": hit_rate
            }
        except Exception as e:
            JLogger.error("Redis health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_celery_health() -> Dict:
        """Check Celery worker health"""
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            active = inspect.active()
            
            if not stats:
                return {
                    "status": "unhealthy",
                    "error": "No workers available"
                }
            
            worker_count = len(stats)
            total_active = sum(len(tasks) for tasks in active.values()) if active else 0
            
            return {
                "status": "healthy",
                "active_workers": worker_count,
                "pending_tasks": total_active,
                "workers": list(stats.keys())
            }
        except Exception as e:
            JLogger.error("Celery health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @staticmethod
    def check_disk_health() -> Dict:
        """Check disk space"""
        try:
            disk = psutil.disk_usage('/')
            
            return {
                "status": "healthy" if disk.percent < 90 else "warning",
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent_used": disk.percent
            }
        except Exception as e:
            JLogger.error("Disk health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    @classmethod
    def get_overall_health(cls) -> Dict:
        """Get overall system health"""
        db = SessionLocal()
        try:
            components = {
                "database": cls.check_database_health(db),
                "redis": cls.check_redis_health(),
                "celery": cls.check_celery_health(),
                "disk": cls.check_disk_health()
            }
            
            # Determine overall status
            statuses = [comp["status"] for comp in components.values()]
            if "unhealthy" in statuses:
                overall_status = "unhealthy"
            elif "warning" in statuses:
                overall_status = "degraded"
            else:
                overall_status = "healthy"
            
            return {
                "status": overall_status,
                "timestamp": int(time.time() * 1000),
                "components": components
            }
        finally:
            db.close()
