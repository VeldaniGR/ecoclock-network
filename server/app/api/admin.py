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

@router.get("/users")
async def admin_list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Listado global de usuarios para el portal admin."""
    # Usuarios
    users_result = await db.execute(
        select(User).order_by(User.id.asc())
    )
    users = users_result.scalars().all()

    # Última actividad por user_id (máx. completed_at o Result.created_at)
    last_task = (
        await db.execute(
            select(
                Task.user_id,
                func.max(Task.completed_at).label("last_task_at"),
            )
            .where(Task.user_id.isnot(None))
            .group_by(Task.user_id)
        )
    ).all()
    last_task_map = {row.user_id: row.last_task_at for row in last_task}

    last_result = (
        await db.execute(
            select(
                Task.user_id,
                func.max(Result.created_at).label("last_result_at"),
            )
            .join(Result, Result.task_id == Task.id)
            .where(Task.user_id.isnot(None))
            .group_by(Task.user_id)
        )
    ).all()
    last_result_map = {row.user_id: row.last_result_at for row in last_result}

    # Nodo actual (si pertenece a alguno)
    memberships = (
        await db.execute(
            select(NodeMember.user_id, NodeMember.role, Node.id, Node.name)
            .join(Node, Node.id == NodeMember.node_id)
        )
    ).all()
    node_map = {
        row.user_id: {
            "node_id": row.id,
            "node_name": row.name,
            "role": row.role,
        }
        for row in memberships
    }

    # Créditos totales por usuario (si tienes tabla Credit)
    try:
        from app.db.models import Credit
        credits_rows = (
            await db.execute(
                select(Credit.user_id, func.count().label("credits"))
                .group_by(Credit.user_id)
            )
        ).all()
        credits_map = {row.user_id: row.credits for row in credits_rows}
    except Exception:
        credits_map = {}

    out = []
    for u in users:
        last_a = last_task_map.get(u.id)
        last_b = last_result_map.get(u.id)
        last_active = None
        if last_a and last_b:
            last_active = max(last_a, last_b)
        else:
            last_active = last_a or last_b

        node_info = node_map.get(u.id) or {}
        out.append(
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_superadmin": bool(getattr(u, "is_superadmin", False)),
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_active_at": last_active.isoformat() if last_active else None,
                "credits": credits_map.get(u.id, 0),
                "node_id": node_info.get("node_id"),
                "node_name": node_info.get("node_name"),
                "node_role": node_info.get("role"),
            }
        )

    return {"users": out, "total": len(out)}
