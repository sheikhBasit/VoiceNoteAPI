from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
import stripe
import json
from app.db.session import SessionLocal
from app.db import models
from app.services.billing_service import BillingService
from app.core.config import ai_config
from app.utils.json_logger import JLogger
from typing import Optional

router = APIRouter(prefix="/api/v1/billing", tags=["Monetization"])

@router.get("/wallet")
async def get_wallet(user_id: str):
    """
    Retrieve user balance and recent transactions.
    """
    db = SessionLocal()
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
async def create_checkout_session(user_id: str, amount_credits: int):
    """
    Create a Stripe Checkout session for topping up credits.
    1 credit = $0.01 (1 cent) for simplicity.
    """
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
