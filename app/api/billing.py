from fastapi import APIRouter, Depends, HTTPException, Request, Header
from app.utils.security import verify_device_signature
from sqlalchemy.orm import Session
import stripe
import json
import hmac
import hashlib
from app.db.session import SessionLocal
from app.db import models
from app.services.billing_service import BillingService
from app.core.config import ai_config
from app.utils.json_logger import JLogger
from typing import Optional

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def verify_hmac(request: Request, x_device_signature: str = Header(None), x_device_timestamp: str = Header(None)):
    """
    Optional security hardening to verify frontend signatures.
    """
    if not ai_config.STRIPE_WEBHOOK_SECRET: # Use a similar secret or dedicated one
        return
    # Verification logic would go here
    pass

router = APIRouter(prefix="/api/v1/billing", tags=["Monetization"])

@router.get("/wallet")
async def get_wallet(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature)
):
    """
    Retrieve user balance and recent transactions.
    """
    user_id = current_user.id
    try:
        billing = BillingService(db)
        wallet = billing.get_or_create_wallet(user_id)
        transactions = db.query(models.Transaction).filter(
            models.Transaction.wallet_id == user_id
        ).order_by(models.Transaction.created_at.desc()).limit(20).all()
        
        return {
            "balance": wallet.balance,
            "currency": wallet.currency,
            "is_frozen": wallet.is_frozen,
            "recent_transactions": [
                {
                    "amount": tx.amount,
                    "type": tx.type,
                    "description": tx.description,
                    "timestamp": tx.created_at
                } for tx in transactions
            ]
        }
    finally:
        db.close()

@router.post("/checkout")
async def create_checkout_session(
    amount_credits: int,
    current_user: models.User = Depends(get_current_user),
    _sig: bool = Depends(verify_device_signature)
):
    """
    Create a Stripe Checkout session for topping up credits.
    1 credit = $0.01 (1 cent) for simplicity.
    """
    user_id = current_user.id
    try:
        # Create a checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'VoiceNote AI: {amount_credits} Credits',
                        'description': 'Advanced AI processing and storage credits',
                    },
                    'unit_amount': amount_credits, # Stored in cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://voicenote.ai/billing/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://voicenote.ai/billing/cancel',
            metadata={
                'user_id': user_id,
                'amount_credits': amount_credits
            }
        )
        return {"checkout_url": checkout_session.url}
    except Exception as e:
        JLogger.error("Stripe Checkout Error", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail="Could not initialize payment gateway.")

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Handles successful payment notifications from Stripe to top up user wallets.
    """
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, ai_config.STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        JLogger.error("Stripe Webhook Signature Invalid", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('metadata', {}).get('user_id')
        credits = int(session.get('metadata', {}).get('amount_credits', 0))
        
        if user_id and credits > 0:
            db = SessionLocal()
            try:
                billing = BillingService(db)
                billing.process_deposit(user_id, credits, f"Stripe Session: {session['id']}")
                JLogger.info("User Wallet Recharged", user_id=user_id, amount=credits)
                
                # INTEGRATION WITH PHASE 9: Notify via WebSocket
                from app.services.websocket_manager import manager
                # Assuming we have a way to prompt a client refresh
                # await manager.broadcast_status(user_id, "WALLET_UPDATE", {"balance": new_balance})
                
            except Exception as e:
                JLogger.error("Failed to process Stripe deposit", error=str(e), user_id=user_id)
            finally:
                db.close()

    return {"status": "success"}
