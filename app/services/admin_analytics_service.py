"""
Admin Analytics Service
Handles usage analytics, growth trends, and revenue reporting
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.db.models import (
    Note,
    SubscriptionTier,
    Task,
    Transaction,
    UsageLog,
    User,
    Wallet,
)
from app.utils.json_logger import JLogger


class AdminAnalyticsService:
    """Service for admin analytics and reporting"""

    # ============================================================================
    # USAGE ANALYTICS
    # ============================================================================

    @staticmethod
    def get_usage_analytics(
        db: Session,
        start_date: int,
        end_date: int,
        group_by: str = "day"
    ) -> Dict:
        """
        Get usage analytics for a date range
        
        Args:
            start_date: Start timestamp (ms)
            end_date: End timestamp (ms)
            group_by: Grouping (day, week, month)
        """
        # Get usage logs in date range
        usage_logs = db.query(UsageLog).filter(
            and_(
                UsageLog.timestamp >= start_date,
                UsageLog.timestamp <= end_date
            )
        ).all()
        
        # Calculate totals
        total_audio_minutes = sum((log.duration_seconds or 0) / 60 for log in usage_logs)
        total_api_calls = len(usage_logs)
        
        # Get notes created in range
        notes_created = db.query(Note).filter(
            and_(
                Note.timestamp >= start_date,
                Note.timestamp <= end_date
            )
        ).count()
        
        # Get tasks created in range
        tasks_created = db.query(Task).filter(
            and_(
                Task.created_at >= start_date,
                Task.created_at <= end_date
            )
        ).count()
        
        # Get active users in range
        active_users = db.query(User).filter(
            and_(
                User.last_login >= start_date,
                User.last_login <= end_date
            )
        ).count()
        
        # Group by time period
        usage_by_period = {}
        if group_by == "day":
            # Group by day
            for log in usage_logs:
                day = datetime.fromtimestamp(log.timestamp / 1000).strftime("%Y-%m-%d")
                if day not in usage_by_period:
                    usage_by_period[day] = {
                        "audio_minutes": 0,
                        "api_calls": 0
                    }
                usage_by_period[day]["audio_minutes"] += (log.duration_seconds or 0) / 60
                usage_by_period[day]["api_calls"] += 1
        
        return {
            "total_audio_minutes": round(total_audio_minutes, 2),
            "total_api_calls": total_api_calls,
            "notes_created": notes_created,
            "tasks_created": tasks_created,
            "active_users": active_users,
            "usage_by_period": usage_by_period,
            "date_range": {
                "start": start_date,
                "end": end_date,
                "group_by": group_by
            }
        }

    # ============================================================================
    # GROWTH ANALYTICS
    # ============================================================================

    @staticmethod
    def get_growth_analytics(db: Session) -> Dict:
        """Get growth trends and metrics"""
        
        # Get signups by month (last 12 months)
        twelve_months_ago = int((time.time() - 365 * 24 * 60 * 60) * 1000)
        
        users = db.query(User).filter(
            User.last_login >= twelve_months_ago
        ).all()
        
        signups_by_month = {}
        for user in users:
            month = datetime.fromtimestamp(user.last_login / 1000).strftime("%Y-%m")
            signups_by_month[month] = signups_by_month.get(month, 0) + 1
        
        # Get tier distribution
        tier_distribution = {}
        for tier in SubscriptionTier:
            count = db.query(User).filter(
                User.tier == tier,
                User.is_deleted == False
            ).count()
            tier_distribution[tier.name] = count
        
        # Get retention metrics (users active in last 30 days)
        thirty_days_ago = int((time.time() - 30 * 24 * 60 * 60) * 1000)
        active_last_30d = db.query(User).filter(
            User.last_login >= thirty_days_ago,
            User.is_deleted == False
        ).count()
        
        total_users = db.query(User).filter(User.is_deleted == False).count()
        retention_rate = (active_last_30d / total_users * 100) if total_users > 0 else 0
        
        # Get churn (deleted users in last 30 days)
        churned_users = db.query(User).filter(
            User.is_deleted == True,
            User.deleted_at >= thirty_days_ago
        ).count()
        
        churn_rate = (churned_users / total_users * 100) if total_users > 0 else 0
        
        return {
            "signups_by_month": signups_by_month,
            "tier_distribution": tier_distribution,
            "retention": {
                "active_last_30d": active_last_30d,
                "total_users": total_users,
                "retention_rate_percent": round(retention_rate, 2)
            },
            "churn": {
                "churned_last_30d": churned_users,
                "churn_rate_percent": round(churn_rate, 2)
            }
        }

    # ============================================================================
    # REVENUE ANALYTICS
    # ============================================================================

    @staticmethod
    def get_revenue_report(
        db: Session,
        start_date: int,
        end_date: int
    ) -> Dict:
        """
        Get revenue report for date range
        
        Args:
            start_date: Start timestamp (ms)
            end_date: End timestamp (ms)
        """
        # Get all transactions in range
        transactions = db.query(Transaction).filter(
            and_(
                Transaction.created_at >= start_date,
                Transaction.created_at <= end_date
            )
        ).all()
        
        # Calculate revenue (deposits/refunds = positive inflow)
        credits = [t for t in transactions if t.type in ("DEPOSIT", "REFUND", "BONUS")]
        total_revenue = sum(t.amount for t in credits)

        # Calculate expenses (usage = negative outflow)
        debits = [t for t in transactions if t.type == "USAGE"]
        total_expenses = sum(abs(t.amount) for t in debits)
        
        # Net revenue
        net_revenue = total_revenue - total_expenses
        
        # Revenue by tier
        revenue_by_tier = {}
        for tier in SubscriptionTier:
            tier_users = db.query(User).filter(User.tier == tier).all()
            tier_user_ids = [u.id for u in tier_users]
            
            tier_revenue = sum(
                t.amount for t in credits 
                if t.wallet_id in tier_user_ids
            )
            revenue_by_tier[tier.name] = tier_revenue
        
        # Average revenue per user
        total_users = db.query(User).filter(User.is_deleted == False).count()
        arpu = (total_revenue / total_users) if total_users > 0 else 0
        
        # Transaction count
        transaction_count = len(transactions)
        
        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_revenue": net_revenue,
            "revenue_by_tier": revenue_by_tier,
            "arpu": round(arpu, 2),
            "transaction_count": transaction_count,
            "date_range": {
                "start": start_date,
                "end": end_date
            }
        }

    # ============================================================================
    # USER BEHAVIOR ANALYTICS
    # ============================================================================

    @staticmethod
    def get_user_behavior_analytics(db: Session) -> Dict:
        """Get user behavior insights"""
        
        # Most active users (by note count)
        top_users_by_notes = db.query(
            User.id,
            User.name,
            User.email,
            func.count(Note.id).label("note_count")
        ).join(Note).filter(
            User.is_deleted == False,
            Note.is_deleted == False
        ).group_by(User.id).order_by(
            func.count(Note.id).desc()
        ).limit(10).all()
        
        # Average notes per user
        total_notes = db.query(Note).filter(Note.is_deleted == False).count()
        total_users = db.query(User).filter(User.is_deleted == False).count()
        avg_notes_per_user = (total_notes / total_users) if total_users > 0 else 0
        
        # Average tasks per user
        total_tasks = db.query(Task).filter(Task.is_deleted == False).count()
        avg_tasks_per_user = (total_tasks / total_users) if total_users > 0 else 0
        
        # Peak usage hours (from usage logs)
        usage_logs = db.query(UsageLog).limit(1000).all()
        hour_distribution = {}
        for log in usage_logs:
            hour = datetime.fromtimestamp(log.timestamp / 1000).hour
            hour_distribution[hour] = hour_distribution.get(hour, 0) + 1
        
        # Most popular features (based on usage logs endpoint field)
        feature_usage = {}
        for log in usage_logs:
            if log.endpoint:
                feature_usage[log.endpoint] = feature_usage.get(log.endpoint, 0) + 1
        
        return {
            "top_users_by_notes": [
                {
                    "user_id": row[0],
                    "name": row[1],
                    "email": row[2],
                    "note_count": row[3]
                }
                for row in top_users_by_notes
            ],
            "averages": {
                "notes_per_user": round(avg_notes_per_user, 2),
                "tasks_per_user": round(avg_tasks_per_user, 2)
            },
            "peak_usage_hours": hour_distribution,
            "feature_usage": feature_usage
        }

    # ============================================================================
    # SYSTEM METRICS
    # ============================================================================

    @staticmethod
    def get_system_metrics(db: Session) -> Dict:
        """Get overall system metrics"""
        
        # Storage usage (estimate from notes)
        notes_with_audio = db.query(Note).filter(
            Note.audio_url.isnot(None)
        ).count()
        
        # Estimate: average 1MB per note
        estimated_storage_mb = notes_with_audio * 1
        
        # Database size (approximate from record counts)
        total_notes = db.query(Note).count()
        total_tasks = db.query(Task).count()
        total_users = db.query(User).count()
        total_transactions = db.query(Transaction).count()
        
        total_records = total_notes + total_tasks + total_users + total_transactions
        
        return {
            "storage": {
                "notes_with_audio": notes_with_audio,
                "estimated_storage_mb": estimated_storage_mb,
                "estimated_storage_gb": round(estimated_storage_mb / 1024, 2)
            },
            "database": {
                "total_records": total_records,
                "notes": total_notes,
                "tasks": total_tasks,
                "users": total_users,
                "transactions": total_transactions
            }
        }
