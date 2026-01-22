class UserBase(BaseModel):
    id: str
    name: str
    email: str
    primary_role: UserRole = UserRole.GENERIC
    secondary_role: Optional[UserRole] = None
    custom_role_description: str = ""
    system_prompt: str = ""
    jargons: List[str] = []
    show_floating_button: bool = True
    work_start_hour: int = 9
    work_end_hour: int = 17
    work_days: List[int] = [2, 3, 4, 5, 6]
    # Admin fields (NEW)
    is_admin: bool = False
    admin_permissions: Optional[Dict[str, any]] = None

class UserCreate(UserBase):
    token: str
    device_id: str
    device_model: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    primary_role: Optional[UserRole] = None
    system_prompt: Optional[str] = None
    work_start_hour: Optional[int] = None
    work_end_hour: Optional[int] = None