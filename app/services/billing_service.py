import stripe
from sqlalchemy.orm import Session
from app.db.models import Wallet, Transaction, User
from app.core.config import ai_config
import logging
from typing import Optional
import uuid

logger = logging.getLogger("VoiceNote.Billing")

# Initialize Stripe
stripe.api_key = ai_config.STRIPE_SECRET_KEY

class BillingService:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_wallet(self, user_id: str) -> Wallet:
        wallet = self.db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            logger.info(f"Creating new wallet for user {user_id}")
            wallet = Wallet(user_id=user_id, balance=100) # Give 100 free credits on signup
            self.db.add(wallet)
            self.db.commit()
            self.db.refresh(wallet)
        return wallet

    def check_balance(self, user_id: str, estimated_cost: int) -> bool:
        """
        Returns True if user has enough credits.
        """
        wallet = self.get_or_create_wallet(user_id)
        if wallet.is_frozen:
            return False
            
        return wallet.balance >= estimated_cost

    def charge_usage(self, user_id: str, cost: int, description: str, ref_id: Optional[str] = None) -> bool:
        """
        Deducts credits from wallet and logs transaction.
        """
        wallet = self.get_or_create_wallet(user_id)
        
        if wallet.balance < cost:
            logger.warning(f"Insufficient funds for user {user_id}: Needs {cost}, has {wallet.balance}")
            return False
            
        # Deduct balance
        wallet.balance -= cost
        
        # Log Transaction
        tx = Transaction(
            wallet_id=wallet.user_id,
            amount=-cost,
            balance_after=wallet.balance,
            type="USAGE",
            description=description,
            reference_id=ref_id
        )
        self.db.add(tx)
        
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
        wallet = self.get_or_create_wallet(user_id)
        wallet.balance += amount
        
        tx = Transaction(
            wallet_id=wallet.user_id,
            amount=amount,
            balance_after=wallet.balance,
            type="DEPOSIT",
            description=f"Deposit via {source}",
            reference_id=str(uuid.uuid4())
        )
        self.db.add(tx)
        self.db.commit()
        return wallet
