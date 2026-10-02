"""Endpoints del usuario autenticado: créditos, perfil, etc."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Credit, User
from app.schemas import CreditsSummary, CreditOut

router = APIRouter()


@router.get("/credits", response_model=CreditsSummary)
async def get_my_credits(
	limit: int = Query(
		10,
		ge=1,
		le=100,
		description="Número máximo de créditos recientes a devolver (1-100).",
	),
	db: AsyncSession = Depends(get_db),
	current_user: User = Depends(get_current_user),
):
	"""Devuelve el resumen de créditos del usuario autenticado."""
	# Total acumulado (sum de amount, 0.0 si no hay créditos).
	total_row = await db.execute(
		select(func.coalesce(func.sum(Credit.amount), 0.0)).where(
			Credit.user_id == current_user.id
		)
	)
	total = float(total_row.scalar_one())

	# Créditos recientes, ordenados por granted_at DESC.
	rows = await db.execute(
		select(Credit)
		.where(Credit.user_id == current_user.id)
		.order_by(Credit.granted_at.desc())
		.limit(limit)
	)
	recent = rows.scalars().all()

	return CreditsSummary(
		user_id=current_user.id,
		username=current_user.username,
		total=total,
		recent=[CreditOut.model_validate(c, from_attributes=True) for c in recent],
	)
