"""Endpoints del usuario autenticado: créditos, perfil, etc."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Credit, Result, Task, User
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

    # Contadores por client_mode / client (tabla results + tasks del usuario)
    mode_rows = await db.execute(
        select(
            func.coalesce(Result.client_mode, "unknown"),
            func.count(),
        )
        .join(Task, Task.id == Result.task_id)
        .where(Task.user_id == current_user.id)
        .group_by(func.coalesce(Result.client_mode, "unknown"))
    )
    by_mode = {str(k): int(v) for k, v in mode_rows.all()}

    client_rows = await db.execute(
        select(
            func.coalesce(Result.client, "unknown"),
            func.count(),
        )
        .join(Task, Task.id == Result.task_id)
        .where(Task.user_id == current_user.id)
        .group_by(func.coalesce(Result.client, "unknown"))
    )
    by_client = {str(k): int(v) for k, v in client_rows.all()}

    return CreditsSummary(
        user_id=current_user.id,
        username=current_user.username,
        total=total,
        recent=[CreditOut.model_validate(c, from_attributes=True) for c in recent],
        by_mode=by_mode,
        by_client=by_client,
    )
