import requests
import sys
import os
from dotenv import load_dotenv

# Load env before imports that might rely on config
load_dotenv()

# Add app to path to import models
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.db.models import User, Wallet

BASE_URL = "http://localhost:8001"

def setup_poor_user():
    db = SessionLocal()
    try:
        user_id = "poor_guy"
        # 1. Ensure User Exists
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"Creating user {user_id}...")
            user = User(id=user_id, email="poor@example.com", password_hash="pw")
            db.add(user)
            db.commit()
        
        # 2. Ensure Wallet Exists with 0 Balance
        wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
        if not wallet:
            print(f"Creating wallet for {user_id}...")
            wallet = Wallet(user_id=user_id, balance=0)
            db.add(wallet)
        else:
            print(f"Updating balance for {user_id} to 0...")
            wallet.balance = 0
        
        db.commit()
        print("Poor user setup complete.")
    except Exception as e:
        print(f"Setup failed: {e}")
        db.rollback()
    finally:
        db.close()

def test_payment_enforcement():
    setup_poor_user()
    print("=== Testing Payment Enforcement Middleware ===")
    
    # 1. Test with a Rich User (Should Pass Billing -> 401 Auth)
    print("\n1. Testing Rich User (admin_main)...")
    # We rely on "admin_main" existing from previous seeds with default 100 credits (created by middleware if missing)
    # Actually, admin_main might not have a wallet yet. Middleware creates it with 100.
    # But admin_main MUST exist in User table. Assuming yes.
    headers = {"X-User-ID": "admin_main"} 
    try:
        res = requests.get(f"{BASE_URL}/api/v1/notes", headers=headers)
        print(f"Result: {res.status_code} (Expected 401 or 200)")
        if res.status_code in [200, 401]:
             print("SUCCESS: Passed Billing Check.")
        else:
             print(f"FAILURE: Unexpected code {res.status_code}")
    except Exception as e:
        print(f"Failed: {e}")

    # 2. Test with Poor User (Should Fail Billing -> 402)
    print("\n2. Testing Poor User (poor_guy)...")
    headers = {"X-User-ID": "poor_guy"}
    try:
        # Notes endpoint costs 1 credit, balance is 0
        res = requests.get(f"{BASE_URL}/api/v1/notes", headers=headers)
        print(f"Result: {res.status_code} (Expected 402)")
        if res.status_code == 402:
            print("SUCCESS: Payment Required returned.")
        else:
            print(f"FAILURE: Expected 402, got {res.status_code}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_payment_enforcement()
