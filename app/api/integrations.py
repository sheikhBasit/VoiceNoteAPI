import logging
import os
import time
import uuid
import requests
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from sqlalchemy.orm import Session
from app.db import models
from app.db.session import get_db
from app.services.auth_service import get_current_user
from app.core.limiter import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/integrations", tags=["Integrations"])

# Configuration (Env Vars usually)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "mock_client_id")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "mock_client_secret")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/integrations/google/callback")


@router.get("/list")
def list_integrations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List connected services."""
    integrations = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id
    ).all()
    
    return [
        {
            "provider": i.provider,
            "connected_at": i.created_at,
            "scope": i.scope,
            "meta_data": i.meta_data,
            "active": True
        }
        for i in integrations
    ]


@router.post("/google/connect")
@limiter.limit("5/minute")
def connect_google(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Connect Google Account.
    Payload: {"code": "auth_code_from_google"}
    """
    code = payload.get("code")
    access_token = payload.get("access_token")
    
    if not code and not access_token:
         raise HTTPException(status_code=400, detail="Missing authorization code or access token")

    tokens = {}
    
    if code:
        # Exchange code for tokens (Mock logic for now, or real if env vars set)
        if GOOGLE_CLIENT_ID == "mock_client_id":
             # Mock Exchange
             tokens = {
                "access_token": f"mock_google_access_{current_user.id}_{int(time.time())}",
                "refresh_token": f"mock_google_refresh_{current_user.id}_{int(time.time())}",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/calendar.events"
            }
        else:
            # Real Exchange
            try:
                token_url = "https://oauth2.googleapis.com/token"
                data = {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                }
                resp = requests.post(token_url, data=data)
                resp.raise_for_status()
                tokens = resp.json()
            except Exception as e:
                logger.error(f"Google Token Exchange Failed: {e}")
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
    else:
        # Direct Access Token provided
        tokens = {
            "access_token": access_token,
            "refresh_token": payload.get("refresh_token"), # Optional
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/calendar.events"
        }

    # Save to DB
    existing = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "google"
    ).first()

    if existing:
        existing.access_token = tokens["access_token"]
        existing.refresh_token = tokens.get("refresh_token", existing.refresh_token)
        # Calculate expiry
        expires_in = tokens.get("expires_in", 3600)
        existing.expires_at = int(time.time() * 1000) + (expires_in * 1000)
        existing.updated_at = int(time.time() * 1000)
    else:
        expires_in = tokens.get("expires_in", 3600)
        new_integration = models.UserIntegration(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider="google",
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            expires_at=int(time.time() * 1000) + (expires_in * 1000),
            scope=tokens.get("scope", "calendar"),
            meta_data={}
        )
        db.add(new_integration)
    
    db.commit()
    return {"status": "connected", "provider": "google"}


@router.post("/notion/connect")
@limiter.limit("5/minute")
def connect_notion(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Connect Notion Workspace.
    Payload: {"code": "..."}
    """
    code = payload.get("code")
    if not code:
         raise HTTPException(status_code=400, detail="Missing authorization code")

    # Mock Exchange
    tokens = {
        "access_token": f"mock_notion_access_{current_user.id}_{int(time.time())}",
        "workspace_name": "Demo Workspace",
        "bot_id": "mock_bot_id"
    }
    
    existing = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == "notion"
    ).first()

    if existing:
        existing.access_token = tokens["access_token"]
        existing.meta_data = {
            "workspace_name": tokens["workspace_name"],
            "bot_id": tokens["bot_id"]
        }
        existing.updated_at = int(time.time() * 1000)
    else:
        new_integration = models.UserIntegration(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            provider="notion",
            access_token=tokens["access_token"],
            meta_data={
                "workspace_name": tokens["workspace_name"],
                "bot_id": tokens["bot_id"]
            }
        )
        db.add(new_integration)
    
    db.commit()
    return {"status": "connected", "provider": "notion"}


@router.delete("/{provider}/disconnect")
def disconnect_integration(
    provider: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Disconnect an integration."""
    integration = db.query(models.UserIntegration).filter(
        models.UserIntegration.user_id == current_user.id,
        models.UserIntegration.provider == provider
    ).first()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    db.delete(integration)
    db.commit()
    
    return {"status": "disconnected", "provider": provider}
