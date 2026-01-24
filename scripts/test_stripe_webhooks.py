import requests
import time
import json
import stripe
import os
import sys
from dotenv import load_dotenv

# Load env
load_dotenv()
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.db.models import User, Wallet
from app.core.config import ai_config

BASE_URL = "http://localhost:8001"
WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_placeholder_secret_replace_me")

def setup_test_data():
    db = SessionLocal()
    # Ensure user exists
    user_id = "test_webhook_user"
    customer_id = "cus_test_123"
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        user = User(id=user_id, email="webhook@test.com", password_hash="pw")
        db.add(user)
    
    # Ensure wallet exists and link to stripe customer
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0, stripe_customer_id=customer_id)
        db.add(wallet)
    else:
        wallet.stripe_customer_id = customer_id
        # Reset balance for test
        wallet.balance = 0
    
    db.commit()
    db.close()
    return user_id, customer_id

def generate_signature(payload: str, secret: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload}"
    signature = stripe.WebhookSignature._compute_signature(signed_payload, secret)
    return f"t={timestamp},v1={signature}"

def test_invoice_payment():
    print("=== Testing Stripe Invoice Payment Webhook ===")
    user_id, customer_id = setup_test_data()
    
    # Payload
    payload_dict = {
        "id": "evt_test_invoice",
        "object": "event",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": "in_test_123",
                "object": "invoice",
                "amount_paid": 5000, # $50.00
                "customer": customer_id,
                "status": "paid"
            }
        }
    }
    payload_str = json.dumps(payload_dict)
    
    # Generate Header
    sig_header = generate_signature(payload_str, WEBHOOK_SECRET)
    headers = {
        "Stripe-Signature": sig_header,
        "Content-Type": "application/json"
    }
    
    # Send Request
    try:
        res = requests.post(f"{BASE_URL}/webhooks/stripe", data=payload_str, headers=headers)
        print(f"Webhook Response: {res.status_code}")
        if res.status_code == 200:
            print("Webhook accepted.")
        else:
            print(f"Webhook failed: {res.text}")
            return

        # Verify Balance Update
        # Give a small delay for DB commit if async/background (though here it is sync)
        time.sleep(1)
        
        db = SessionLocal()
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        print(f"Wallet Balance: {wallet.balance} (Expected 5000)")
        
        if wallet.balance == 5000:
            print("SUCCESS: Wallet funded.")
        else:
            print("FAILURE: Incorrect balance.")
        db.close()

    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    test_invoice_payment()
