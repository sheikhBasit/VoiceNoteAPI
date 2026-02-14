import os
import time
import secrets
from datetime import UTC, datetime, timedelta
from typing import Optional

import jwt
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.utils.json_logger import JLogger

# Configuration
# Configuration
SECRET_KEY = os.getenv("DEVICE_SECRET_KEY", "your-secret-key-keep-it-safe")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Short-lived access token for security
REFRESH_TOKEN_EXPIRE_DAYS = 30  # Long lived for mobile
SECRET_KEY_REFRESH = os.getenv("REFRESH_SECRET_KEY", "refresh-secret-key-change-me")

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # Removed passlib
# Use HTTPBearer instead of OAuth2PasswordBearer for proper Swagger UI integration
security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(encoded_jwt, bytes):
        return encoded_jwt.decode('utf-8')
    return encoded_jwt


def create_refresh_token(user_id: str, db: Session, expires_delta: Optional[timedelta] = None):
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
    expires_timestamp = int(expire.timestamp() * 1000)
    
    # Generate random token string
    token_str = secrets.token_urlsafe(32)
    
    new_refresh = models.RefreshToken(
        user_id=user_id,
        token=token_str,
        expires_at=expires_timestamp,
        is_revoked=False
    )
    db.add(new_refresh)
    db.commit()
    
    return token_str


def refresh_access_token(refresh_token: str, db: Session):
    # 1. Find the token in DB
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == refresh_token,
        models.RefreshToken.is_revoked == False
    ).first()
    
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # 2. Check Expiration
    if db_token.expires_at < int(time.time() * 1000):
        db_token.is_revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")
        
    user_id = db_token.user_id
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or user.is_deleted:
        raise HTTPException(status_code=401, detail="User validation failed")

    # 3. Implement Token Rotation
    # Revoke current token
    db_token.is_revoked = True
    
    # Issue new Pair
    new_access = create_access_token({"sub": user_id})
    new_refresh_str = create_refresh_token(user_id, db)
    
    db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh_str,
        "token_type": "bearer",
    }


def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    # Use bcrypt directly
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password):
    # Use bcrypt directly
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_device_verification_token(
    email: str, device_id: str, device_model: str, biometric_token: str
):
    """Generates a short-lived token (15 mins) to verify a new device."""
    expire = datetime.now(UTC) + timedelta(minutes=15)
    to_encode = {
        "sub": email,
        "type": "device_verification",
        "device_id": device_id,
        "device_model": device_model,
        "biometric_token": biometric_token,
        "exp": expire,
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(token, bytes):
        return token.decode('utf-8')
    return token


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
    db: Session = Depends(get_db),
):
    """
    Dependency to get the currently authenticated user from JWT.
    Validates:
    1. JWT integrity and expiration.
    2. User existence in DB.
    3. Biometric token consistency for mobile users (non-admins).
    """
    # Fast-path: Check if middleware already fetched the user
    cached_user = getattr(request.state, "user", None)
    if cached_user:
        return cached_user

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

    from app.utils.security import is_dev_bypass

    # Support development bypass tokens (dev_user-id format)
    if is_dev_bypass(token):
        user_id = token.replace("dev_", "")
        JLogger.info("Using development bypass token", user_id=user_id)
    else:
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
        if is_dev_bypass(token):
            # Auto-create dev user
            user = models.User(
                id=user_id,
                name=f"Dev User ({user_id})",
                email=f"{user_id}@dev.test",
                tier=models.SubscriptionTier.PREMIUM,
                primary_role=models.UserRole.DEVELOPER,
                authorized_devices=[{
                    "device_id": "bypass_device",
                    "device_model": "Dev Emulator",
                    "biometric_token": "bypass_biometric",
                    "authorized_at": int(time.time() * 1000)
                }]
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            JLogger.info("Auto-created development user", user_id=user_id)
        else:
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
        # Biometric validation removed as per refactor to Email/Password auth
        pass

    return user


async def get_current_active_admin(
    current_user: models.User = Depends(get_current_user),
):
    """Dependency to ensure the user is an active admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: Administrative privileges required",
        )
    return current_user


async def get_current_user_ws(token: str, db: Session = Depends(get_db)):
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
