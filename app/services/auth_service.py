import os
from datetime import datetime, timedelta
from typing import Optional, Any, Union
import jwt
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import models
from app.utils.json_logger import JLogger
import hmac
import hashlib

# Configuration
SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "your-secret-key-keep-it-safe")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Use HTTPBearer instead of OAuth2PasswordBearer for proper Swagger UI integration
security = HTTPBearer(auto_error=False)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_device_verification_token(email: str, device_id: str, device_model: str, biometric_token: str):
    """Generates a short-lived token (15 mins) to verify a new device."""
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {
        "sub": email,
        "type": "device_verification",
        "device_id": device_id,
        "device_model": device_model,
        "biometric_token": biometric_token,
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_device_token(token: str) -> dict:
    """Decodes and validates a device verification token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "device_verification":
            raise Exception("Invalid token type")
        return payload
    except Exception as e:
        return None

def mock_send_verification_email(email: str, link: str):
    """
    Mocks sending an email. In production, use SMTP or SendGrid.
    """
    print(f"\n[EMAIL SERVICE] To: {email}")
    print(f"Subject: Verify New Device Login")
    print(f"Body: Click here to authorize your new device: {link}\n")
    JLogger.info("Sent verification email", email=email, link=link)

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Dependency to get the currently authenticated user from JWT.
    Validates:
    1. JWT integrity and expiration.
    2. User existence in DB.
    3. Biometric token consistency for mobile users (non-admins).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract token from HTTPBearer credentials
    token = None
    if credentials:
        token = credentials.credentials
    
    # Support token in header if not found (for manual testing)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
        )
    if user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated",
        )

    # Security check: Biometric token consistency for App Users
    if not user.is_admin:
        request_biometric = request.headers.get("X-Biometric-Token")
        if request_biometric:
            # Check if any authorized device has this token
            authorized_devices = user.authorized_devices or []
            device_authorized = any(d.get("biometric_token") == request_biometric for d in authorized_devices)
            
            # For strict security, we'd also check if it matches the CURRENT device.
            # But for now, ensuring it belongs to the user is the baseline.
            if not device_authorized:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Biometric session invalid or changed"
                )

    return user


async def get_current_active_admin(
    current_user: models.User = Depends(get_current_user)
):
    """Dependency to ensure the user is an active admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required"
        )
    return current_user

async def get_current_user_ws(
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket-specific authentication handler.
    Validates JWT for real-time stream connections.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate WebSocket credentials",
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None or user.is_deleted:
        raise credentials_exception
        
    return user
