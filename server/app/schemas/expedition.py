from datetime import datetime
from pydantic import BaseModel


class ExpeditionOut(BaseModel):
    id: int
    slug: str
    name: str
    description: str | None = None
    task_type: str | None = None
    goal_value: int
    current_value: int
    progress: float  # 0.0 – 1.0
    reward_frame: str | None = None
    reward_badge_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    completed_at: datetime | None = None
    is_active: bool
    is_completed: bool

    model_config = {"from_attributes": True}
