import logging
import time
import uuid
from typing import Optional

import stripe
from sqlalchemy.orm import Session

from app.core.config import ai_config
from app.db.models import Transaction, User, Wallet, UsageLog

logger = logging.getLogger("VoiceNote.Billing")

# Initialize Stripe
stripe.api_key = ai_config.STRIPE_SECRET_KEY


class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_wallet(self, user_id: str, for_update: bool = False) -> Wallet:
        query = self.db.query(Wallet).filter(Wallet.user_id == user_id)
        if for_update:
            query = query.with_for_update()
        wallet = query.first()
        if not wallet:
            logger.info(f"Creating new wallet for user {user_id}")
            wallet = Wallet(
                user_id=user_id, balance=100
            )  # Give 100 free credits on signup
            self.db.add(wallet)
            self.db.commit()
            self.db.refresh(wallet)
        return wallet

    def check_balance(self, user_id: str, estimated_cost: int, for_update: bool = False) -> bool:
        """
        Returns True if user has enough credits.
        If for_update=True, locks the row.
        """
        wallet = self.get_or_create_wallet(user_id, for_update=for_update)
        if wallet.is_frozen:
            return False

        return wallet.balance >= estimated_cost

    def charge_usage(
        self,
        user_id: str,
        cost: Optional[int] = None,
        description: str = "",
        ref_id: Optional[str] = None,
        audio_duration: float = 0.0,
        override_wallet_id: Optional[str] = None,
    ) -> bool:
        """
        Deducts credits from wallet, updates user usage stats, and logs granular usage.
        Supports charging a corporate wallet if override_wallet_id is provided.
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        target_wallet_id = override_wallet_id or user_id

        # Determine cost based on plan if not explicitly provided
        final_cost = cost
        if final_cost is None and audio_duration > 0:
            # Fetch price from plan. Default to 10 if no plan.
            rate = (
                user.plan.price_per_minute
                if (user.plan and user.plan.price_per_minute)
                else 10
            )
            final_cost = max(1, int(audio_duration / 60.0 * rate))

        if not final_cost:
            final_cost = 0

        # Atomic Update: Decrease balance only if sufficient funds
        # We use SELECT ... FOR UPDATE to prevent race conditions on PostgreSQL
        wallet = self.db.query(Wallet).filter(
            Wallet.user_id == target_wallet_id
        ).with_for_update().first()

        if not wallet:
            # Create wallet if missing and try again
            wallet = self.get_or_create_wallet(target_wallet_id)
            # Re-fetch with lock
            wallet = self.db.query(Wallet).filter(
                Wallet.user_id == target_wallet_id
            ).with_for_update().first()

        if wallet.balance < final_cost:
            logger.warning(
                f"Insufficient funds for wallet {target_wallet_id} (charged for user {user_id}): Needs {final_cost}, has {wallet.balance}"
            )
            return False

        wallet.balance -= final_cost
        current_balance = wallet.balance

        # Update User Usage Stats (Cache) - always attributed to the person who did it
        if not user.usage_stats:
            user.usage_stats = {
                "total_audio_minutes": 0.0,
                "total_notes": 0,
                "total_tasks": 0,
                "last_usage_at": None,
            }

        from sqlalchemy.orm.attributes import flag_modified

        stats = user.usage_stats
        stats["total_audio_minutes"] = stats.get("total_audio_minutes", 0) + (
            audio_duration / 60.0
        )
        stats["last_usage_at"] = int(time.time() * 1000)
        flag_modified(user, "usage_stats")

        # Log Transaction
        tx = Transaction(
            wallet_id=target_wallet_id,
            amount=-final_cost,
            balance_after=current_balance,
            type="USAGE",
            description=f"{description} (Charged to {'Corporate' if override_wallet_id else 'Personal'})",
            reference_id=ref_id,
        )
        self.db.add(tx)

        # Log to UsageLog
        usage = UsageLog(
            user_id=user_id,
            endpoint=description.split(":")[0] if ":" in description else "unknown",
            duration_seconds=int(audio_duration),
            cost_estimated=final_cost,
            timestamp=int(time.time() * 1000),
        )
        self.db.add(usage)

        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to charge usage: {e}")
            return False

    def process_deposit(self, user_id: str, amount: int, source: str) -> Wallet:
        """
        Adds credits to wallet from Stripe/Admin.
        """
        wallet = self.get_or_create_wallet(user_id, for_update=True)
        wallet.balance += amount

        tx = Transaction(
            wallet_id=wallet.user_id,
            amount=amount,
            balance_after=wallet.balance,
            type="DEPOSIT",
            description=f"Deposit via {source}",
            reference_id=str(uuid.uuid4()),
        )
        self.db.add(tx)
        self.db.commit()
        return wallet
