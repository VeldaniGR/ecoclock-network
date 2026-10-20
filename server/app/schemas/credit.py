"""Esquemas Pydantic para créditos BOINC-style."""
from datetime import datetime
from pydantic import BaseModel, Field


class CreditOut(BaseModel):
    """Un crédito concedido, en formato de salida."""
    id: int
    amount: float = Field(ge=0, description="Créditos concedidos (no negativo)")
    task_id: int
    granted_at: datetime


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
