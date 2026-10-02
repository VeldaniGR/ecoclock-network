"""Esquemas Pydantic para tareas y resultados."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    name: str
    payload: Dict[str, Any]


class TaskCreate(TaskBase):
    pass


class TaskResponse(BaseModel):
    id: int
    name: str
    payload: Dict[str, Any]
    status: str
    user_id: Optional[int] = None
    created_at: datetime
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskSubmit(BaseModel):
    task_id: int
    output: Dict[str, Any]
    compute_time_sec: Optional[float] = None



class ResultResponse(BaseModel):
    id: int
    task_id: int
    output: Dict[str, Any]
    compute_time_sec: Optional[float] = None
    created_at: datetime
