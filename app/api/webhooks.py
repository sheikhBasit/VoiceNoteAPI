from fastapi import APIRouter, Request, HTTPException, Header
import stripe
from app.core.config import ai_config
from app.services.billing_service import BillingService
from app.db.session import SessionLocal
import logging

router = APIRouter()
logger = logging.getLogger("VoiceNote.Webhooks")

stripe.api_key = ai_config.STRIPE_SECRET_KEY

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """
    Handles Stripe webhooks for:
    - checkout.session.completed (Initial payment)
    - invoice.payment_succeeded (Subscription renewal)
    """
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, ai_config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    db = SessionLocal()
    billing_service = BillingService(db)

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            _handle_checkout_completed(session, billing_service)
            
        elif event["type"] == "invoice.payment_succeeded":
            invoice = event["data"]["object"]
            _handle_invoice_payment(invoice, billing_service)
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

def _handle_checkout_completed(session, billing_service: BillingService):
    """
    Fund wallet after successful checkout.
    """
    # Metadata passed during checkout creation
    user_id = session.get("metadata", {}).get("user_id")
    # Convert amount_total (cents) to credits/tokens logic
    # Simplified: 1 cent = 1 credit (Adjust logic as needed)
    amount_paid = session.get("amount_total", 0) 
    
    if user_id and amount_paid > 0:
        logger.info(f"Funding wallet for user {user_id}: +{amount_paid}")
        billing_service.process_deposit(user_id, amount_paid, "Stripe Checkout")

def _handle_invoice_payment(invoice, billing_service: BillingService):
    """
    Fund wallet on subscription renewal.
    """
    # Requires mapping stripe_customer_id to user_id in DB if metadata is missing
    # For MVP, assuming subscription metadata has user_id or we look it up
    # This part is simplified
    amount_paid = invoice.get("amount_paid", 0)
    customer_id = invoice.get("customer")
    
    # In a real app, look up user by stripe_customer_id
    # user = db.query(Wallet).filter(Wallet.stripe_customer_id == customer_id).first()
    # For now, we log it
    logger.info(f"Subscription renewal for customer {customer_id}: +{amount_paid}")
    # billing_service.process_deposit(user.user_id, amount_paid, "Stripe Subscription")
