from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.services.auth_service import get_current_user
from app.services.billing_service import BillingService
from app.utils.json_logger import JLogger


def requires_tier(minimum_tier: models.SubscriptionTier):
    """
    Dependency that ensures a user has at least the required subscription tier.
    """

    async def tier_dependency(current_user: models.User = Depends(get_current_user)):
        # Define tier hierarchy (higher index = higher tier)
        tier_order = [
            models.SubscriptionTier.GUEST,
            models.SubscriptionTier.FREE,
            models.SubscriptionTier.STANDARD,
            models.SubscriptionTier.PREMIUM,
        ]

        try:
            user_idx = tier_order.index(current_user.tier)
            min_idx = tier_order.index(minimum_tier)

            if user_idx < min_idx:
                JLogger.warning(
                    "Access denied: Insufficient subscription tier",
                    user_id=current_user.id,
                    user_tier=current_user.tier.value,
                    required_tier=minimum_tier.value,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires a {minimum_tier.value} subscription. You are currently on the {current_user.tier.value} plan.",
                )
            return current_user
        except ValueError:
            # Handle case where tier is not in the order list
            raise HTTPException(
                status_code=500, detail="Invalid user subscription tier configuration"
            )

    return tier_dependency


def check_credit_balance(estimated_cost: int):
    """
    Dependency that ensures a user has enough credits for an operation.
    Uses FOR UPDATE lock to prevent race conditions where concurrent
    requests both pass the balance check before either deducts.
    """

    async def balance_dependency(
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user),
    ):
        billing_service = BillingService(db)
        if not billing_service.check_balance(current_user.id, estimated_cost, for_update=True):
            JLogger.warning(
                "Access denied: Insufficient credits",
                user_id=current_user.id,
                cost=estimated_cost,
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient credits. This operation costs {estimated_cost} credits.",
            )
        return current_user

    return balance_dependency
