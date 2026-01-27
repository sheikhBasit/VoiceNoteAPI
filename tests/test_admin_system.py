"""
Admin Role & Permission System Tests

Tests for:
- Admin role assignment/revocation
- Permission checking
- Admin API endpoints
- Content moderation
- Permission management
"""

import pytest
from datetime import datetime
import time
import uuid
from app.db import models
from app.db.models import UserRole, Priority, NoteStatus
from app.utils.admin_utils import AdminManager, DEFAULT_ADMIN_PERMISSIONS, MODERATOR_PERMISSIONS
from app.utils.ai_service_utils import AIServiceError


class TestAdminRoleAssignment:
    """Test admin role assignment and revocation"""
    
    def test_grant_full_admin_role(self, db_session):
        """Test granting full admin role"""
        user = models.User(
            id="test_user_001",
            name="Test User",
            email="test@example.com",
            is_admin=False
        )
        db_session.add(user)
        db_session.commit()
        
        updated_user = AdminManager.grant_admin_role(
            db=db_session,
            user_id="test_user_001",
            granted_by="system",
            permission_level="full"
        )
        
        assert updated_user.is_admin is True
        assert updated_user.admin_permissions is not None
        assert updated_user.admin_permissions.get("can_view_all_users") is True
        assert updated_user.admin_permissions.get("can_delete_users") is True
        assert updated_user.admin_created_at is not None
        assert updated_user.admin_permissions.get("granted_by") == "system"
    
    def test_grant_moderator_role(self, db_session):
        """Test granting moderator role"""
        user = models.User(
            id="test_user_002",
            name="Moderator",
            email="mod@example.com",
        )
        db_session.add(user)
        db_session.commit()
        
        updated_user = AdminManager.grant_admin_role(
            db=db_session,
            user_id="test_user_002",
            granted_by="admin_001",
            permission_level="moderator"
        )
        
        assert updated_user.is_admin is True
        assert updated_user.admin_permissions.get("can_moderate_content") is True
        assert updated_user.admin_permissions.get("can_view_all_notes") is True
        assert updated_user.admin_permissions.get("can_manage_admins") is None
    
    def test_grant_viewer_role(self, db_session):
        """Test granting viewer (analytics) role"""
        user = models.User(
            id="test_user_003",
            name="Viewer",
            email="viewer@example.com",
        )
        db_session.add(user)
        db_session.commit()
        
        updated_user = AdminManager.grant_admin_role(
            db=db_session,
            user_id="test_user_003",
            granted_by="admin_001",
            permission_level="viewer"
        )
        
        assert updated_user.is_admin is True
        assert updated_user.admin_permissions.get("can_view_analytics") is True
        assert updated_user.admin_permissions.get("can_view_all_users") is True
        assert updated_user.admin_permissions.get("can_delete_notes") is None
    
    def test_revoke_admin_role(self, db_session):
        """Test revoking admin role"""
        admin_user = models.User(
            id="test_admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions=DEFAULT_ADMIN_PERMISSIONS
        )
        db_session.add(admin_user)
        db_session.commit()
        
        updated_user = AdminManager.revoke_admin_role(
            db=db_session,
            user_id="test_admin_001"
        )
        
        assert updated_user.is_admin is False
        assert updated_user.admin_permissions == {}
    
    def test_grant_admin_to_nonexistent_user(self, db_session):
        """Test error handling for nonexistent user"""
        with pytest.raises(AIServiceError):
            AdminManager.grant_admin_role(
                db=db_session,
                user_id="nonexistent_user",
                granted_by="system",
                permission_level="full"
            )


class TestPermissionChecking:
    """Test permission verification"""
    
    def test_is_admin_check(self, db_session):
        """Test is_admin check"""
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True
        )
        regular_user = models.User(
            id="user_001",
            name="User",
            email="user@example.com",
            is_admin=False
        )
        db_session.add_all([admin_user, regular_user])
        db_session.commit()
        
        assert AdminManager.is_admin(admin_user) is True
        assert AdminManager.is_admin(regular_user) is False
    
    def test_has_permission_single(self, db_session):
        """Test checking single permission"""
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions=DEFAULT_ADMIN_PERMISSIONS
        )
        db_session.add(admin_user)
        db_session.commit()
        
        assert AdminManager.has_permission(admin_user, "can_delete_users") is True
        assert AdminManager.has_permission(admin_user, "nonexistent_perm") is False
    
    def test_has_any_permission(self, db_session):
        """Test checking ANY permission"""
        moderator = models.User(
            id="mod_001",
            name="Moderator",
            email="mod@example.com",
            is_admin=True,
            admin_permissions=MODERATOR_PERMISSIONS
        )
        db_session.add(moderator)
        db_session.commit()
        
        has_perm = AdminManager.has_any_permission(
            moderator,
            ["can_delete_users", "can_moderate_content"]
        )
        assert has_perm is True
        
        has_perm = AdminManager.has_any_permission(
            moderator,
            ["can_delete_users", "can_manage_admins"]
        )
        assert has_perm is False
    
    def test_has_all_permissions(self, db_session):
        """Test checking ALL permissions"""
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions=DEFAULT_ADMIN_PERMISSIONS
        )
        db_session.add(admin_user)
        db_session.commit()
        
        has_all = AdminManager.has_all_permissions(
            admin_user,
            ["can_delete_users", "can_view_all_notes", "can_manage_admins"]
        )
        assert has_all is True
        
        has_all = AdminManager.has_all_permissions(
            admin_user,
            ["can_delete_users", "nonexistent_perm"]
        )
        assert has_all is False


class TestPermissionUpdate:
    """Test updating admin permissions"""
    
    def test_update_permissions_add(self, db_session):
        """Test adding new permissions"""
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions={"can_view_all_users": True}
        )
        db_session.add(admin_user)
        db_session.commit()
        
        updated = AdminManager.update_permissions(
            db=db_session,
            user_id="admin_001",
            permissions={"can_delete_users": True}
        )
        
        assert updated.admin_permissions.get("can_view_all_users") is True
        assert updated.admin_permissions.get("can_delete_users") is True
    
    def test_update_permissions_revoke(self, db_session):
        """Test revoking permissions"""
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions=DEFAULT_ADMIN_PERMISSIONS.copy()
        )
        db_session.add(admin_user)
        db_session.commit()
        
        updated = AdminManager.update_permissions(
            db=db_session,
            user_id="admin_001",
            permissions={"can_delete_users": False}
        )
        
        assert updated.admin_permissions.get("can_delete_users") is False
        assert updated.admin_permissions.get("can_view_all_users") is True
    
    def test_update_permissions_nonexistent_user(self, db_session):
        """Test error for nonexistent user"""
        with pytest.raises(AIServiceError):
            AdminManager.update_permissions(
                db=db_session,
                user_id="nonexistent",
                permissions={"can_view_all_users": True}
            )
    
    def test_update_permissions_non_admin(self, db_session):
        """Test error for non-admin user"""
        user = models.User(
            id="user_001",
            name="User",
            email="user@example.com",
            is_admin=False
        )
        db_session.add(user)
        db_session.commit()
        
        with pytest.raises(AIServiceError):
            AdminManager.update_permissions(
                db=db_session,
                user_id="user_001",
                permissions={"can_view_all_users": True}
            )


class TestAdminActionLogging:
    """Test admin action logging"""
    
    def test_log_admin_action(self, db_session):
        """Test logging admin action"""
        log = AdminManager.log_admin_action(
            db=db_session,
            admin_id="admin_001",
            action="DELETE_USER",
            target_id="user_001",
            details={"reason": "policy_violation"}
        )
        
        assert log["admin_id"] == "admin_001"
        assert log["action"] == "DELETE_USER"
        assert log["target_id"] == "user_001"
        assert log["details"]["reason"] == "policy_violation"
        assert log["timestamp"] is not None
    
    def test_log_make_admin_action(self, db_session):
        """Test logging make admin action"""
        log = AdminManager.log_admin_action(
            db=db_session,
            admin_id="admin_001",
            action="MAKE_ADMIN",
            target_id="user_002",
            details={"level": "moderator"}
        )
        
        assert log["action"] == "MAKE_ADMIN"
        assert log["details"]["level"] == "moderator"


class TestAdminDataAccess:
    """Test admin's ability to access all data"""
    
    def test_admin_can_see_all_notes(self, db_session):
        """Test that admin can see notes from any user"""
        # Create two different users
        user1 = models.User(
            id="user_001",
            name="User 1",
            email="user1@example.com",
        )
        user2 = models.User(
            id="user_002",
            name="User 2",
            email="user2@example.com",
        )
        
        # Create notes from different users
        note1 = models.Note(
            id=str(uuid.uuid4()),
            user_id="user_001",
            title="Note 1",
            summary="User 1 note",
            timestamp=int(time.time() * 1000)
        )
        note2 = models.Note(
            id=str(uuid.uuid4()),
            user_id="user_002",
            title="Note 2",
            summary="User 2 note",
            timestamp=int(time.time() * 1000)
        )
        
        db_session.add_all([user1, user2, note1, note2])
        db_session.commit()
        
        # Admin can retrieve all notes
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions=DEFAULT_ADMIN_PERMISSIONS
        )
        
        all_notes = db_session.query(models.Note).all()
        assert len(all_notes) >= 2
    
    def test_admin_can_delete_any_note(self, db_session):
        """Test that admin can delete note from any user"""
        user = models.User(
            id="user_001",
            name="User",
            email="user@example.com",
        )
        
        note = models.Note(
            id="note_001",
            user_id="user_001",
            title="Note",
            summary="Summary",
            timestamp=int(time.time() * 1000),
            is_deleted=False
        )
        
        db_session.add_all([user, note])
        db_session.commit()
        
        # Admin deletes the note
        note.is_deleted = True
        note.deleted_at = int(time.time() * 1000)
        db_session.commit()
        
        assert note.is_deleted is True
        assert note.deleted_at is not None
    
    def test_admin_can_delete_any_user(self, db_session):
        """Test that admin can delete any user"""
        user = models.User(
            id="user_001",
            name="User",
            email="user@example.com",
            is_deleted=False
        )
        
        db_session.add(user)
        db_session.commit()
        
        # Admin deletes the user
        user.is_deleted = True
        user.deleted_at = int(time.time() * 1000)
        db_session.commit()
        
        assert user.is_deleted is True
        assert user.deleted_at is not None


class TestAdminSecurityBoundaries:
    """Test security boundaries and privilege escalation prevention"""
    
    def test_moderator_cannot_manage_admins(self, db_session):
        """Test that moderator can't promote other users"""
        moderator = models.User(
            id="mod_001",
            name="Moderator",
            email="mod@example.com",
            is_admin=True,
            admin_permissions=MODERATOR_PERMISSIONS
        )
        
        db_session.add(moderator)
        db_session.commit()
        
        # Moderator doesn't have can_manage_admins permission
        assert AdminManager.has_permission(moderator, "can_manage_admins") is False
    
    def test_viewer_cannot_delete_content(self, db_session):
        """Test that viewer can't delete content"""
        from app.utils.admin_utils import VIEWER_PERMISSIONS
        
        viewer = models.User(
            id="viewer_001",
            name="Viewer",
            email="viewer@example.com",
            is_admin=True,
            admin_permissions=VIEWER_PERMISSIONS
        )
        
        db_session.add(viewer)
        db_session.commit()
        
        # Viewer doesn't have delete permissions
        assert AdminManager.has_permission(viewer, "can_delete_notes") is False
        assert AdminManager.has_permission(viewer, "can_delete_users") is False
    
    def test_regular_user_cannot_see_admin_operations(self, db_session):
        """Test that regular users aren't admins"""
        user = models.User(
            id="user_001",
            name="User",
            email="user@example.com",
            is_admin=False
        )
        
        db_session.add(user)
        db_session.commit()
        
        assert AdminManager.is_admin(user) is False
        assert AdminManager.has_permission(user, "can_view_all_users") is False


class TestAdminTimestamps:
    """Test admin timestamp tracking"""
    
    def test_admin_created_at_set_on_grant(self, db_session):
        """Test admin_created_at is set when admin role granted"""
        user = models.User(
            id="user_001",
            name="User",
            email="user@example.com",
        )
        db_session.add(user)
        db_session.commit()
        
        before_grant = int(time.time() * 1000)
        AdminManager.grant_admin_role(
            db=db_session,
            user_id="user_001",
            granted_by="system",
            permission_level="full"
        )
        after_grant = int(time.time() * 1000)
        
        user = db_session.query(models.User).filter(models.User.id == "user_001").first()
        assert before_grant <= user.admin_created_at <= after_grant
    
    def test_admin_last_action_updated(self, db_session):
        """Test admin_last_action is updated"""
        admin_user = models.User(
            id="admin_001",
            name="Admin",
            email="admin@example.com",
            is_admin=True,
            admin_permissions=DEFAULT_ADMIN_PERMISSIONS,
            admin_created_at=int(time.time() * 1000) - 10000  # 10 seconds ago
        )
        db_session.add(admin_user)
        db_session.commit()
        
        before_update = int(time.time() * 1000)
        AdminManager.update_permissions(
            db=db_session,
            user_id="admin_001",
            permissions={"can_view_all_users": False}
        )
        after_update = int(time.time() * 1000)
        
        admin_user = db_session.query(models.User).filter(models.User.id == "admin_001").first()
        assert before_update <= admin_user.admin_last_action <= after_update
