import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.schemas.billing import (
    ServicePlanResponse,
    VerifyPurchaseRequest,
    VerifyPurchaseResponse,
)
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/billing", tags=["Billing"])


@router.get("/plans", response_model=List[ServicePlanResponse])
def get_available_plans(db: Session = Depends(get_db)):
    """Public endpoint — returns all active subscription plans for the mobile app."""
    plans = (
        db.query(models.ServicePlan)
        .filter(models.ServicePlan.is_active == True)
        .order_by(models.ServicePlan.monthly_credits.asc())
        .all()
    )
    return plans


@router.post("/verify-purchase", response_model=VerifyPurchaseResponse)
def verify_google_play_purchase(
    body: VerifyPurchaseRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Verify a Google Play purchase token and upgrade the user's tier.
    """
    if not body.product_id or not body.purchase_token:
        raise HTTPException(
            status_code=422,
            detail="Validation failed: product_id and purchase_token are required"
        )
    # 1. Find the matching plan by Google Play product ID
    plan = (
        db.query(models.ServicePlan)
        .filter(
            models.ServicePlan.google_play_product_id == body.product_id,
            models.ServicePlan.is_active == True,
        )
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="No plan found for this product ID")

    # TODO: In production, verify purchase token with Google Play Developer API:
    # from google.oauth2 import service_account
    # credentials = service_account.Credentials.from_service_account_file(...)
    # service = build('androidpublisher', 'v3', credentials=credentials)
    # result = service.purchases().subscriptions().get(
    #     packageName='com.example.voicenote',
    #     subscriptionId=body.product_id,
    #     token=body.purchase_token
    # ).execute()

    # 2. Upgrade user tier and assign plan
    current_user.tier = models.SubscriptionTier.PREMIUM
    current_user.plan_id = plan.id
    current_user.updated_at = int(time.time() * 1000)

    # 3. Add monthly credits from the plan to wallet
    wallet = (
        db.query(models.Wallet)
        .filter(models.Wallet.user_id == current_user.id)
        .first()
    )
    if wallet:
        wallet.balance += plan.monthly_credits

        # Record the transaction
        transaction = models.Transaction(
            wallet_id=wallet.user_id,
            amount=plan.monthly_credits,
            type="DEPOSIT",
            description=f"Subscription: {plan.name}",
            reference_id=body.purchase_token[:64],
        )
        db.add(transaction)

    db.commit()

    return VerifyPurchaseResponse(
        success=True,
        new_tier="PREMIUM",
        message=f"Upgraded to {plan.name} plan successfully",
    )
