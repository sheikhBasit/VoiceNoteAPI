"""
Admin Operations Service
Handles API key management, bulk operations, and wallet operations
"""

import time
import uuid
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ApiKey, Note, Task, Transaction, User, Wallet
from app.utils.json_logger import JLogger


class AdminOperationsService:
    """Service for admin operations"""

    # ============================================================================
    # API KEY MANAGEMENT
    # ============================================================================

    @staticmethod
    def list_api_keys(db: Session, service_name: Optional[str] = None) -> Dict:
        """List all API keys"""
        query = db.query(ApiKey)
        
        if service_name:
            query = query.filter(ApiKey.service_name == service_name)
        
        keys = query.order_by(ApiKey.priority.asc()).all()
        
        # Mask the actual keys for security
        masked_keys = []
        for key in keys:
            masked_keys.append({
                "id": key.id,
                "service_name": key.service_name,
                "masked_key": f"{key.api_key[:8]}...{key.api_key[-4:]}" if len(key.api_key) > 12 else "***",
                "priority": key.priority,
                "is_active": key.is_active,
                "error_count": key.error_count,
                "last_error_at": key.last_error_at,
                "notes": key.notes,
                "created_at": key.created_at
            })
        
        return {
            "keys": masked_keys,
            "total": len(masked_keys)
        }

    @staticmethod
    def create_api_key(
        db: Session,
        service_name: str,
        api_key: str,
        priority: int = 1,
        is_active: bool = True,
        notes: Optional[str] = None
    ) -> Dict:
        """Create a new API key"""
        # Validate service name
        valid_services = ["groq", "deepgram", "openai", "anthropic"]
        if service_name not in valid_services:
            raise ValueError(f"Invalid service name. Must be one of: {valid_services}")
        
        new_key = ApiKey(
            id=str(uuid.uuid4()),
            service_name=service_name,
            api_key=api_key,
            priority=priority,
            is_active=is_active,
            notes=notes,
            error_count=0,
            created_at=int(time.time() * 1000)
        )
        
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        
        JLogger.info("API key created", service=service_name, key_id=new_key.id)
        
        return {
            "status": "success",
            "key_id": new_key.id,
            "service_name": service_name
        }

    @staticmethod
    def update_api_key(
        db: Session,
        key_id: str,
        priority: Optional[int] = None,
        is_active: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> Dict:
        """Update an API key"""
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not key:
            raise ValueError("API key not found")
        
        if priority is not None:
            key.priority = priority
        if is_active is not None:
            key.is_active = is_active
        if notes is not None:
            key.notes = notes
        
        db.commit()
        
        return {"status": "success", "key_id": key_id}

    @staticmethod
    def delete_api_key(db: Session, key_id: str) -> Dict:
        """Delete an API key"""
        key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
        if not key:
            raise ValueError("API key not found")
        
        db.delete(key)
        db.commit()
        
        JLogger.info("API key deleted", key_id=key_id)
        
        return {"status": "success", "deleted": True}

    @staticmethod
    def get_api_key_health(db: Session) -> Dict:
        """Get health status of all API keys"""
        keys = db.query(ApiKey).all()
        
        health_report = {}
        for service in ["groq", "deepgram", "openai", "anthropic"]:
            service_keys = [k for k in keys if k.service_name == service]
            active_keys = [k for k in service_keys if k.is_active]
            error_keys = [k for k in service_keys if k.error_count > 5]
            
            health_report[service] = {
                "total_keys": len(service_keys),
                "active_keys": len(active_keys),
                "error_keys": len(error_keys),
                "status": "healthy" if len(active_keys) > 0 else "warning"
            }
        
        return {"health_report": health_report}

    # ============================================================================
    # BULK OPERATIONS
    # ============================================================================

    @staticmethod
    def bulk_delete(
        db: Session,
        item_type: str,
        ids: List[str],
        admin_id: str,
        reason: str,
        hard: bool = False
    ) -> Dict:
        """Bulk delete items"""
        if item_type not in ["notes", "tasks", "users"]:
            raise ValueError("Invalid item type. Must be: notes, tasks, or users")
        
        deleted_count = 0
        
        if item_type == "notes":
            if hard:
                deleted_count = db.query(Note).filter(Note.id.in_(ids)).delete(synchronize_session=False)
            else:
                deleted_count = db.query(Note).filter(Note.id.in_(ids)).update(
                    {"is_deleted": True, "deleted_at": int(time.time() * 1000)},
                    synchronize_session=False
                )
        
        elif item_type == "tasks":
            if hard:
                deleted_count = db.query(Task).filter(Task.id.in_(ids)).delete(synchronize_session=False)
            else:
                deleted_count = db.query(Task).filter(Task.id.in_(ids)).update(
                    {"is_deleted": True, "deleted_at": int(time.time() * 1000)},
                    synchronize_session=False
                )
        
        elif item_type == "users":
            if hard:
                raise ValueError("Hard delete not allowed for users. Use soft delete only.")
            deleted_count = db.query(User).filter(User.id.in_(ids)).update(
                {"is_deleted": True, "deleted_at": int(time.time() * 1000)},
                synchronize_session=False
            )
        
        db.commit()
        
        JLogger.info(
            "Bulk delete completed",
            type=item_type,
            count=deleted_count,
            hard=hard,
            admin_id=admin_id
        )
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "type": item_type,
            "hard": hard
        }

    @staticmethod
    def bulk_restore(
        db: Session,
        item_type: str,
        ids: List[str],
        admin_id: str
    ) -> Dict:
        """Bulk restore soft-deleted items"""
        if item_type not in ["notes", "tasks", "users"]:
            raise ValueError("Invalid item type. Must be: notes, tasks, or users")
        
        restored_count = 0
        
        if item_type == "notes":
            restored_count = db.query(Note).filter(
                Note.id.in_(ids),
                Note.is_deleted == True
            ).update(
                {"is_deleted": False, "deleted_at": None},
                synchronize_session=False
            )
        
        elif item_type == "tasks":
            restored_count = db.query(Task).filter(
                Task.id.in_(ids),
                Task.is_deleted == True
            ).update(
                {"is_deleted": False, "deleted_at": None},
                synchronize_session=False
            )
        
        elif item_type == "users":
            restored_count = db.query(User).filter(
                User.id.in_(ids),
                User.is_deleted == True
            ).update(
                {"is_deleted": False, "deleted_at": None},
                synchronize_session=False
            )
        
        db.commit()
        
        JLogger.info(
            "Bulk restore completed",
            type=item_type,
            count=restored_count,
            admin_id=admin_id
        )
        
        return {
            "status": "success",
            "restored_count": restored_count,
            "type": item_type
        }

    # ============================================================================
    # WALLET MANAGEMENT
    # ============================================================================

    @staticmethod
    def list_wallets(
        db: Session,
        limit: int = 20,
        skip: int = 0,
        is_frozen: Optional[bool] = None
    ) -> Dict:
        """List all wallets"""
        query = db.query(Wallet).join(User)
        
        if is_frozen is not None:
            query = query.filter(Wallet.is_frozen == is_frozen)
        
        total = query.count()
        wallets = query.offset(skip).limit(limit).all()
        
        wallet_list = []
        for wallet in wallets:
            wallet_list.append({
                "user_id": wallet.user_id,
                "balance": wallet.balance,
                "currency": wallet.currency,
                "is_frozen": wallet.is_frozen,
                "user_email": wallet.user.email if wallet.user else None,
                "user_name": wallet.user.name if wallet.user else None
            })
        
        return {
            "wallets": wallet_list,
            "total": total,
            "limit": limit,
            "skip": skip
        }

    @staticmethod
    def credit_wallet(
        db: Session,
        user_id: str,
        amount: int,
        admin_id: str,
        reason: str
    ) -> Dict:
        """Credit a user's wallet"""
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        
        if not wallet:
            # Create wallet if it doesn't exist
            wallet = Wallet(
                user_id=user_id,
                balance=0,
                currency="USD",
                is_frozen=False
            )
            db.add(wallet)
        
        wallet.balance += amount
        
        # Create transaction record
        transaction = Transaction(
            wallet_id=wallet.user_id,
            amount=amount,
            balance_after=wallet.balance,
            type="ADMIN_CREDIT",
            description=f"Admin credit: {reason}",
            reference_id=None
        )
        db.add(transaction)
        
        db.commit()
        
        JLogger.info(
            "Wallet credited",
            user_id=user_id,
            amount=amount,
            admin_id=admin_id,
            reason=reason
        )
        
        return {
            "status": "success",
            "new_balance": wallet.balance,
            "amount_credited": amount
        }

    @staticmethod
    def debit_wallet(
        db: Session,
        user_id: str,
        amount: int,
        admin_id: str,
        reason: str
    ) -> Dict:
        """Debit a user's wallet"""
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        
        if not wallet:
            raise ValueError("Wallet not found")
        
        if wallet.balance < amount:
            raise ValueError("Insufficient balance")
        
        wallet.balance -= amount
        
        # Create transaction record
        transaction = Transaction(
            wallet_id=wallet.user_id,
            amount=-amount,
            balance_after=wallet.balance,
            type="ADMIN_DEBIT",
            description=f"Admin debit: {reason}",
            reference_id=None
        )
        db.add(transaction)
        
        db.commit()
        
        JLogger.info(
            "Wallet debited",
            user_id=user_id,
            amount=amount,
            admin_id=admin_id,
            reason=reason
        )
        
        return {
            "status": "success",
            "new_balance": wallet.balance,
            "amount_debited": amount
        }

    @staticmethod
    def freeze_wallet(
        db: Session,
        user_id: str,
        admin_id: str,
        reason: str
    ) -> Dict:
        """Freeze a user's wallet"""
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        
        if not wallet:
            raise ValueError("Wallet not found")
        
        wallet.is_frozen = True
        db.commit()
        
        JLogger.info(
            "Wallet frozen",
            user_id=user_id,
            admin_id=admin_id,
            reason=reason
        )
        
        return {
            "status": "success",
            "is_frozen": True
        }

    @staticmethod
    def unfreeze_wallet(
        db: Session,
        user_id: str,
        admin_id: str
    ) -> Dict:
        """Unfreeze a user's wallet"""
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        
        if not wallet:
            raise ValueError("Wallet not found")
        
        wallet.is_frozen = False
        db.commit()
        
        JLogger.info(
            "Wallet unfrozen",
            user_id=user_id,
            admin_id=admin_id
        )
        
        return {
            "status": "success",
            "is_frozen": False
        }
