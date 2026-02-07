from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.db.models import UserRole


class UserBase(BaseModel):
    id: str
    name: str
    email: str
    primary_role: UserRole = UserRole.GENERIC
    secondary_role: Optional[UserRole] = None
    custom_role_description: Optional[str] = ""
    system_prompt: Optional[str] = ""
    jargons: List[str] = []
    show_floating_button: Optional[bool] = True
    work_start_hour: int = 9
    work_end_hour: int = 17
    work_days: List[int] = [2, 3, 4, 5, 6]
    work_days: List[int] = [2, 3, 4, 5, 6]
    timezone: str = "UTC"
    profile_picture_url: Optional[str] = None
    # Admin fields (NEW)
    # is_admin: bool = False
    # admin_permissions: Optional[Dict[str, Any]] = None


class UserCreate(UserBase):
    id: Optional[str] = None
    token: str
    device_id: str
    device_model: str
    timezone: Optional[str] = "UTC"  # Optional, defaults to UTC


class UserUpdate(BaseModel):
    name: Optional[str] = None
    primary_role: Optional[UserRole] = None
    system_prompt: Optional[str] = None
    work_start_hour: Optional[int] = None
    work_end_hour: Optional[int] = None
    timezone: Optional[str] = None


class UserResponse(UserBase):
    last_login: Optional[int] = None
    is_deleted: bool = False
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AdminLogin(BaseModel):
    username: str
    password: str


class SyncResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    is_new_user: bool = False
    model_config = ConfigDict(from_attributes=True)
