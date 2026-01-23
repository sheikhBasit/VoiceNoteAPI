"""
V-Model Integration Tests - API Endpoint Cascade Deletion

Tests the API endpoints for proper cascade behavior and referential integrity.
V-Model Level: Integration Testing (Middle level)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.main import app
from app.db.session import get_db, Base
from app.db import models
import uuid
import time
from sqlalchemy import String

# --- SQLite Patches (Same as Unit Tests) ---
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

import sqlalchemy.dialects.sqlite.base as sqlite_base
sqlite_base.SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"
sqlite_base.SQLiteTypeCompiler.visit_VECTOR = lambda self, type_, **kw: "TEXT"

SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

class TestEndpointCascadeIntegration:
    """Integration tests for API endpoints."""

    def test_user_deletion_cascades_api(self, client, db_session):
        """Test DELETE /api/v1/users/me cascades via API."""
        # 1. Setup Data
        user_id = f"user_{uuid.uuid4()}"
        user = models.User(id=user_id, name="Integration User", email=f"int_{uuid.uuid4()}@ex.com")
        db_session.add(user)
        
        note_id = str(uuid.uuid4())
        note = models.Note(id=note_id, user_id=user_id, title="Int Note")
        db_session.add(note)
        
        task_id = str(uuid.uuid4())
        task = models.Task(id=task_id, note_id=note_id, description="Int Task")
        db_session.add(task)
        db_session.commit()
        
        # 2. Call API (Soft Delete)
        response = client.delete(f"/api/v1/users/me?user_id={user_id}&hard=false")
        assert response.status_code == 200
        
        # 3. Verify Cascade
        db_session.expire_all()
        user_db = db_session.query(models.User).get(user_id)
        note_db = db_session.query(models.Note).get(note_id)
        task_db = db_session.query(models.Task).get(task_id)
        
        assert user_db.is_deleted is True
        assert note_db.is_deleted is True
        assert task_db.is_deleted is True

    def test_note_deletion_cascades_api(self, client, db_session):
        """Test DELETE /api/v1/notes/{id} cascades to tasks."""
        # 1. Setup
        user_id = f"user_{uuid.uuid4()}"
        user = models.User(id=user_id, name="Note User", email=f"note_{uuid.uuid4()}@ex.com")
        db_session.add(user)
        
        note_id = str(uuid.uuid4())
        note = models.Note(id=note_id, user_id=user_id, title="Target Note")
        db_session.add(note)
        
        task1_id = str(uuid.uuid4())
        task1 = models.Task(id=task1_id, note_id=note_id, description="Task 1")
        db_session.add(task1)
        db_session.commit()
        
        # 2. Delete Note
        response = client.delete(f"/api/v1/notes/{note_id}?user_id={user_id}")
        assert response.status_code == 200
        
        # 3. Verify
        db_session.expire_all()
        note_db = db_session.query(models.Note).get(note_id)
        task_db = db_session.query(models.Task).get(task1_id)
        
        assert note_db.is_deleted is True
        assert task_db.is_deleted is True
        assert note_db.user.is_deleted is False # User remains

    def test_restoration_cascade_api(self, client, db_session):
        """Test PATCH /api/v1/users/{id}/restore restores everything."""
        # 1. Setup Deleted State
        user_id = f"user_{uuid.uuid4()}"
        user = models.User(id=user_id, name="Restorable", is_deleted=True, deleted_at=123)
        db_session.add(user)
        note = models.Note(id=str(uuid.uuid4()), user_id=user_id, is_deleted=True)
        db_session.add(note)
        db_session.commit()
        
        # 2. Restore
        response = client.patch(f"/api/v1/users/{user_id}/restore")
        assert response.status_code == 200
        
        # 3. Verify
        db_session.expire_all()
        user_db = db_session.query(models.User).get(user_id)
        assert user_db.is_deleted is False
        assert db_session.query(models.Note).filter(models.Note.user_id == user_id).first().is_deleted is False

    def test_deletion_integrity_protection(self, client, db_session):
        """Test protection against deleting notes with high priority tasks."""
        # 1. Setup Note with High Priority Task
        user_id = "integrity_user"
        user = models.User(id=user_id, name="IUser", email="i@ex.com")
        db_session.add(user)
        
        note_id = "protected_note"
        note = models.Note(id=note_id, user_id=user_id, title="Protected")
        db_session.add(note)
        
        task = models.Task(
            id="high_task", 
            note_id=note_id, 
            priority=models.Priority.HIGH, 
            is_done=False
        )
        db_session.add(task)
        db_session.commit()
        
        # 2. Attempt Deletion
        response = client.delete(f"/api/v1/notes/{note_id}?user_id={user_id}")
        
        # 3. Should Fail
        assert response.status_code == 400
        assert "HIGH priority tasks" in response.json()["detail"]
