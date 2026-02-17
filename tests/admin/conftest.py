"""
Admin test fixtures
"""

import pytest
from sqlalchemy.orm import Session

from app.db import models
from app.services.auth_service import create_access_token


@pytest.fixture(scope="function")
def admin_token(db: Session):
    """Create admin user and return auth token"""
    # Create admin user
    admin_user = models.User(
        id="admin_test_123",
        email="admin@test.com",
        name="Test Admin",
        is_admin=True,
        admin_permissions={
            "can_view_analytics": True,
            "can_delete_tasks": True,
            "can_restore_tasks": True,
            "can_create_test_notes": True,
            "can_manage_api_keys": True,
            "can_manage_wallets": True,
        }
    )
    db.add(admin_user)
    db.commit()
    
    # Generate token
    token = create_access_token(data={"sub": admin_user.id})
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_user(db: Session):
    """Create regular test user"""
    user = models.User(
        id="user_test_456",
        email="user@test.com",
        name="Test User",
        is_admin=False
    )
    db.add(user)
    db.commit()
    
    return user


@pytest.fixture(scope="function", autouse=True)
def reset_admin_logs(db: Session):
    """Reset admin logs before each test"""
    db.query(models.AdminActionLog).delete()
    db.commit()
    yield
    db.query(models.AdminActionLog).delete()
    db.commit()


@pytest.fixture(scope="function")
def test_note(db: Session, test_user):
    """Create test note for bulk operations"""
    note = models.Note(
        id="note_test_789",
        user_id=test_user.id,
        title="Test Note",
        summary="Test summary",
        transcript_groq="Test transcript"
    )
    db.add(note)
    db.commit()
    
    return note
