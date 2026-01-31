from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any

class ServicePlanBase(BaseModel):
    id: str
    name: str
    price_per_minute: int = 10
    monthly_credits: int = 100
    ai_models_allowed: List[str] = ["llama-3.1", "nova-2"]
    can_use_rag: bool = True
    max_storage_mb: int = 500

class ServicePlanCreate(ServicePlanBase):
    pass

class ServicePlanResponse(ServicePlanBase):
    created_at: int
    updated_at: int
    model_config = ConfigDict(from_attributes=True)

class UsageLogResponse(BaseModel):
    id: int
    user_id: str
    endpoint: str
    duration_seconds: int
    cost_estimated: int
    timestamp: int
    model_config = ConfigDict(from_attributes=True)

class UserUsageSummary(BaseModel):
    user_id: str
    email: str
    name: str
    usage_stats: Optional[dict] = None
    wallet_balance: int
    plan_name: Optional[str] = None
