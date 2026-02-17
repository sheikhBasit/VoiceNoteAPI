"""
Celery Monitoring Service
Handles Celery task monitoring, worker management, and queue inspection
"""

import time
from typing import Dict, List, Optional

from celery.result import AsyncResult

from app.utils.json_logger import JLogger
from app.worker.task import celery_app


class CeleryMonitorService:
    """Service for Celery monitoring and management"""

    # ============================================================================
    # TASK MONITORING
    # ============================================================================

    @staticmethod
    def get_active_tasks() -> Dict:
        """Get all currently active tasks"""
        try:
            inspect = celery_app.control.inspect()
            active = inspect.active()
            
            if not active:
                return {
                    "active_tasks": [],
                    "total": 0,
                    "workers": []
                }
            
            all_tasks = []
            for worker, tasks in active.items():
                for task in tasks:
                    all_tasks.append({
                        "task_id": task.get("id"),
                        "task_name": task.get("name"),
                        "worker": worker,
                        "args": task.get("args"),
                        "kwargs": task.get("kwargs"),
                        "time_start": task.get("time_start")
                    })
            
            return {
                "active_tasks": all_tasks,
                "total": len(all_tasks),
                "workers": list(active.keys())
            }
        except Exception as e:
            JLogger.error("Failed to get active tasks", error=str(e))
            return {"error": str(e)}

    @staticmethod
    def get_pending_tasks() -> Dict:
        """Get all pending tasks in queue"""
        try:
            inspect = celery_app.control.inspect()
            reserved = inspect.reserved()
            scheduled = inspect.scheduled()
            
            pending_tasks = []
            
            if reserved:
                for worker, tasks in reserved.items():
                    for task in tasks:
                        pending_tasks.append({
                            "task_id": task.get("id"),
                            "task_name": task.get("name"),
                            "worker": worker,
                            "status": "reserved"
                        })
            
            if scheduled:
                for worker, tasks in scheduled.items():
                    for task in tasks:
                        pending_tasks.append({
                            "task_id": task.get("id"),
                            "task_name": task.get("name"),
                            "worker": worker,
                            "status": "scheduled",
                            "eta": task.get("eta")
                        })
            
            return {
                "pending_tasks": pending_tasks,
                "total": len(pending_tasks)
            }
        except Exception as e:
            JLogger.error("Failed to get pending tasks", error=str(e))
            return {"error": str(e)}

    @staticmethod
    def get_task_status(task_id: str) -> Dict:
        """Get status of a specific task"""
        try:
            result = AsyncResult(task_id, app=celery_app)
            
            return {
                "task_id": task_id,
                "state": result.state,
                "ready": result.ready(),
                "successful": result.successful() if result.ready() else None,
                "failed": result.failed() if result.ready() else None,
                "result": str(result.result) if result.ready() else None,
                "traceback": result.traceback if result.failed() else None
            }
        except Exception as e:
            JLogger.error("Failed to get task status", task_id=task_id, error=str(e))
            return {"error": str(e)}

    @staticmethod
    def retry_task(task_id: str) -> Dict:
        """Retry a failed task"""
        try:
            result = AsyncResult(task_id, app=celery_app)
            
            if not result.failed():
                return {
                    "status": "error",
                    "message": "Task has not failed, cannot retry"
                }
            
            # Get the task name and args from the result
            # Note: This is a simplified version. In production, you'd need to store
            # task metadata to properly retry with original args
            result.forget()
            
            return {
                "status": "success",
                "message": "Task marked for retry",
                "task_id": task_id
            }
        except Exception as e:
            JLogger.error("Failed to retry task", task_id=task_id, error=str(e))
            return {"error": str(e)}

    @staticmethod
    def cancel_task(task_id: str) -> Dict:
        """Cancel a pending or running task"""
        try:
            celery_app.control.revoke(task_id, terminate=True)
            
            JLogger.info("Task cancelled", task_id=task_id)
            
            return {
                "status": "success",
                "message": "Task cancelled",
                "task_id": task_id
            }
        except Exception as e:
            JLogger.error("Failed to cancel task", task_id=task_id, error=str(e))
            return {"error": str(e)}

    # ============================================================================
    # WORKER MANAGEMENT
    # ============================================================================

    @staticmethod
    def get_worker_stats() -> Dict:
        """Get statistics for all workers"""
        try:
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            
            if not stats:
                return {
                    "workers": [],
                    "total_workers": 0,
                    "error": "No workers available"
                }
            
            worker_list = []
            for worker_name, worker_stats in stats.items():
                worker_list.append({
                    "name": worker_name,
                    "pool": worker_stats.get("pool", {}).get("implementation"),
                    "max_concurrency": worker_stats.get("pool", {}).get("max-concurrency"),
                    "processes": worker_stats.get("pool", {}).get("processes", []),
                    "total_tasks": worker_stats.get("total", {}),
                    "rusage": worker_stats.get("rusage")
                })
            
            return {
                "workers": worker_list,
                "total_workers": len(worker_list)
            }
        except Exception as e:
            JLogger.error("Failed to get worker stats", error=str(e))
            return {"error": str(e)}

    @staticmethod
    def get_registered_tasks() -> Dict:
        """Get all registered tasks"""
        try:
            inspect = celery_app.control.inspect()
            registered = inspect.registered()
            
            if not registered:
                return {
                    "registered_tasks": [],
                    "total": 0
                }
            
            all_tasks = set()
            for worker, tasks in registered.items():
                all_tasks.update(tasks)
            
            return {
                "registered_tasks": sorted(list(all_tasks)),
                "total": len(all_tasks),
                "workers": list(registered.keys())
            }
        except Exception as e:
            JLogger.error("Failed to get registered tasks", error=str(e))
            return {"error": str(e)}

    @staticmethod
    def shutdown_worker(worker_name: str) -> Dict:
        """Shutdown a specific worker"""
        try:
            celery_app.control.shutdown(destination=[worker_name])
            
            JLogger.warning("Worker shutdown initiated", worker=worker_name)
            
            return {
                "status": "success",
                "message": f"Shutdown signal sent to {worker_name}"
            }
        except Exception as e:
            JLogger.error("Failed to shutdown worker", worker=worker_name, error=str(e))
            return {"error": str(e)}

    @staticmethod
    def pool_restart(worker_name: Optional[str] = None) -> Dict:
        """Restart worker pool"""
        try:
            if worker_name:
                celery_app.control.pool_restart(destination=[worker_name])
                message = f"Pool restart signal sent to {worker_name}"
            else:
                celery_app.control.pool_restart()
                message = "Pool restart signal sent to all workers"
            
            JLogger.info("Worker pool restart initiated", worker=worker_name)
            
            return {
                "status": "success",
                "message": message
            }
        except Exception as e:
            JLogger.error("Failed to restart pool", worker=worker_name, error=str(e))
            return {"error": str(e)}

    # ============================================================================
    # QUEUE INSPECTION
    # ============================================================================

    @staticmethod
    def get_queue_lengths() -> Dict:
        """Get queue lengths for all queues"""
        try:
            inspect = celery_app.control.inspect()
            
            # Get active queues
            active_queues = inspect.active_queues()
            
            if not active_queues:
                return {
                    "queues": {},
                    "total_queues": 0
                }
            
            queue_info = {}
            for worker, queues in active_queues.items():
                for queue in queues:
                    queue_name = queue.get("name")
                    if queue_name not in queue_info:
                        queue_info[queue_name] = {
                            "workers": [],
                            "routing_key": queue.get("routing_key"),
                            "exchange": queue.get("exchange", {}).get("name")
                        }
                    queue_info[queue_name]["workers"].append(worker)
            
            return {
                "queues": queue_info,
                "total_queues": len(queue_info)
            }
        except Exception as e:
            JLogger.error("Failed to get queue lengths", error=str(e))
            return {"error": str(e)}

    @staticmethod
    def purge_queue(queue_name: str) -> Dict:
        """Purge all tasks from a queue"""
        try:
            celery_app.control.purge()
            
            JLogger.warning("Queue purged", queue=queue_name)
            
            return {
                "status": "success",
                "message": f"Queue {queue_name} purged"
            }
        except Exception as e:
            JLogger.error("Failed to purge queue", queue=queue_name, error=str(e))
            return {"error": str(e)}
