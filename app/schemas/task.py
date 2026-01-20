class TaskBase(BaseModel):
    description: str
    priority: Priority = Priority.MEDIUM
    deadline: Optional[int] = None
    google_prompt: str = ""
    ai_prompt: str = ""
    assigned_contact_name: Optional[str] = None
    assigned_contact_phone: Optional[str] = None
    communication_type: Optional[CommunicationType] = None
    communication_scheduled_time: Optional[int] = None
    custom_url: Optional[str] = None

class TaskCreate(TaskBase):
    note_id: str
    image_url: Optional[str] = None
    document_urls: List[str] = []

class TaskResponse(TaskBase):
    id: str
    is_done: bool
    is_action_approved: bool
    created_at: int
    image_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)