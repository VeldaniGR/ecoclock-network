"""Esquemas Pydantic para créditos BOINC-style."""
from datetime import datetime
from pydantic import BaseModel, Field


class CreditOut(BaseModel):
    """Un crédito concedido, en formato de salida."""
    id: int
    amount: float = Field(ge=0, description="Créditos concedidos (no negativo)")
    task_id: int
    granted_at: datetime


class LevelInfo(BaseModel):
    id: int
    name: str
    next_id: int | None = None
    next_name: str | None = None
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Avance hacia el siguiente nivel")


class AchievementOut(BaseModel):
    id: str
    name: str
    unlocked_at: datetime | None = None


class CreditsSummary(BaseModel):
    """Resumen de créditos del usuario autenticado."""
    user_id: int
    username: str
    total: float = Field(ge=0, description="Suma total de créditos del usuario")
    recent: list[CreditOut] = Field(
        default_factory=list,
        description="Últimos créditos concedidos (más recientes primero)",
    )
    by_mode: dict[str, int] = Field(
        default_factory=dict,
        description="Conteo de resultados: manual | auto | unknown",
    )
    by_client: dict[str, int] = Field(
        default_factory=dict,
        description="Conteo de resultados: flutter_mobile | gui | cli | unknown",
    )
    # Dashboard / gamificación (fase A)
    tasks_done: int = Field(0, ge=0, description="Resultados enviados por el usuario")
    credits_this_week: float = Field(
        0, ge=0, description="Créditos concedidos desde el lunes 00:00 UTC"
    )
    streak_days: int = Field(
        0, ge=0, description="Días consecutivos UTC con al menos un crédito"
    )
    last_active_at: datetime | None = Field(
        None, description="Última concesión de crédito"
    )
    # Fase B
    active_days: int = Field(0, ge=0, description="Días distintos con al menos un crédito")
    task_types: list[str] = Field(
        default_factory=list,
        description="Tipos de tarea vistos (ej. ndvi, posidonia)",
    )
    level: LevelInfo | None = None
    achievements: list[AchievementOut] = Field(default_factory=list)