"""Endpoints de administración global (solo superadmin)."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_superadmin
from app.db.database import get_db
from app.db.models import Node, NodeMember, Result, Task, User

router = APIRouter(prefix="/admin", tags=["admin"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/summary")
async def admin_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    since_24h = _utcnow() - timedelta(hours=24)

    total_users = (
        await db.execute(select(func.count()).select_from(User))
    ).scalar_one()

    total_nodes = (
        await db.execute(select(func.count()).select_from(Node))
    ).scalar_one()

    active_24h = (
        await db.execute(
            select(func.count(func.distinct(Task.user_id)))
            .select_from(Result)
            .join(Task, Task.id == Result.task_id)
            .where(Result.created_at >= since_24h)
            .where(Task.user_id.isnot(None))
        )
    ).scalar_one()

    auto_24h = (
        await db.execute(
            select(func.count())
            .select_from(Result)
            .where(Result.created_at >= since_24h)
            .where(Result.client_mode == "auto")
        )
    ).scalar_one()

    tasks_completed_24h = (
        await db.execute(
            select(func.count())
            .select_from(Result)
            .where(Result.created_at >= since_24h)
        )
    ).scalar_one()

    users_in_node = (
        await db.execute(
            select(func.count(func.distinct(NodeMember.user_id)))
        )
    ).scalar_one()

    return {
        "total_users": total_users,
        "total_nodes": total_nodes,
        "users_in_node": users_in_node,
        "active_users_24h": active_24h,
        "tasks_completed_24h": tasks_completed_24h,
        "auto_results_24h": auto_24h,
    }
