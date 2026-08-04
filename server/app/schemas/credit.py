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
