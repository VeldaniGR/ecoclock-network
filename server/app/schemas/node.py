from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NodeCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=80)


class NodePublic(BaseModel):
    id: int
    name: str
    logo_url: Optional[str] = None
    member_count: int
    is_public: bool

    class Config:
        from_attributes = True


class NodeDetail(NodePublic):
    invite_code: str
    created_at: datetime
    my_role: str  # "admin" | "member"


class NodeMemberOut(BaseModel):
    user_id: int
    username: str
    role: str
    joined_at: datetime

    class Config:
        from_attributes = True


class JoinRequestOut(BaseModel):
    id: int
    user_id: int
    username: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TransferLeadership(BaseModel):
    new_admin_user_id: int
