from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class ServicePlanBase(BaseModel):
    id: str
    name: str
    price_per_minute: int = 10
    monthly_credits: int = 100
    ai_models_allowed: List[str] = ["llama-3.1", "nova-2"]
    can_use_rag: bool = True
    max_storage_mb: int = 500
    google_play_product_id: Optional[str] = None
    description: Optional[str] = None
    monthly_note_limit: int = 10
    monthly_task_limit: int = 20
    features: Dict[str, Any] = {}
    is_active: bool = True


class ServicePlanCreate(ServicePlanBase):
    pass


class ServicePlanUpdate(BaseModel):
    name: Optional[str] = None
    price_per_minute: Optional[int] = None
    monthly_credits: Optional[int] = None
    ai_models_allowed: Optional[List[str]] = None
    can_use_rag: Optional[bool] = None
    max_storage_mb: Optional[int] = None
    google_play_product_id: Optional[str] = None
    description: Optional[str] = None
    monthly_note_limit: Optional[int] = None
    monthly_task_limit: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ServicePlanResponse(ServicePlanBase):
    created_at: int
    updated_at: int
    model_config = ConfigDict(from_attributes=True)


class VerifyPurchaseRequest(BaseModel):
    purchase_token: str
    product_id: str


class VerifyPurchaseResponse(BaseModel):
    success: bool
    new_tier: Optional[str] = None
    message: str


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
