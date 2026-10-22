"""Endpoints del usuario autenticado: créditos, perfil, etc."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Credit, Result, Task, User
from app.schemas import CreditsSummary, CreditOut
from app.services.gamification import compute_level, compute_achievements

router = APIRouter()


def _week_start_utc(now: datetime | None = None) -> datetime:
    """Lunes 00:00 UTC de la semana ISO en curso."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    monday = now.date() - timedelta(days=now.weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)


def _compute_streak(active_dates: set) -> int:
    """Racha hacia atrás desde hoy o ayer (UTC date)."""
    if not active_dates:
        return 0
    today = datetime.now(timezone.utc).date()
    start = today if today in active_dates else today - timedelta(days=1)
    if start not in active_dates:
        return 0
    streak = 0
    d = start
    while d in active_dates:
        streak += 1
        d -= timedelta(days=1)
    return streak


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
    total_row = await db.execute(
        select(func.coalesce(func.sum(Credit.amount), 0.0)).where(
            Credit.user_id == current_user.id
        )
    )
    total = float(total_row.scalar_one())

    rows = await db.execute(
        select(Credit)
        .where(Credit.user_id == current_user.id)
        .order_by(Credit.granted_at.desc())
        .limit(limit)
    )
    recent = rows.scalars().all()

    mode_rows = await db.execute(
        select(Result.client_mode, func.count())
        .join(Task, Task.id == Result.task_id)
        .where(Task.user_id == current_user.id)
        .group_by(Result.client_mode)
    )
    by_mode: dict[str, int] = {}
    for key, cnt in mode_rows.all():
        label = key if key else "unknown"
        by_mode[label] = by_mode.get(label, 0) + int(cnt)

    client_rows = await db.execute(
        select(Result.client, func.count())
        .join(Task, Task.id == Result.task_id)
        .where(Task.user_id == current_user.id)
        .group_by(Result.client)
    )
    by_client: dict[str, int] = {}
    for key, cnt in client_rows.all():
        label = key if key else "unknown"
        by_client[label] = by_client.get(label, 0) + int(cnt)

    # tasks_done
    tasks_row = await db.execute(
        select(func.count())
        .select_from(Result)
        .join(Task, Task.id == Result.task_id)
        .where(Task.user_id == current_user.id)
    )
    tasks_done = int(tasks_row.scalar_one() or 0)

    # credits this week (lunes UTC)
    week_start = _week_start_utc()
    week_start_naive = week_start.replace(tzinfo=None)
    week_row = await db.execute(
        select(func.coalesce(func.sum(Credit.amount), 0.0)).where(
            Credit.user_id == current_user.id,
            Credit.granted_at >= week_start_naive,
        )
    )
    credits_this_week = float(week_row.scalar_one())

    # last_active + fechas para racha
    last_row = await db.execute(
        select(func.max(Credit.granted_at)).where(Credit.user_id == current_user.id)
    )
    last_active_at = last_row.scalar_one_or_none()

    day_rows = await db.execute(
        select(func.date(Credit.granted_at))
        .where(Credit.user_id == current_user.id)
        .distinct()
    )
    active_dates = set()
    for (d,) in day_rows.all():
        if d is None:
            continue
        if hasattr(d, "year"):
            active_dates.add(d)
        else:
            # string "YYYY-MM-DD"
            active_dates.add(datetime.strptime(str(d)[:10], "%Y-%m-%d").date())

    streak_days = _compute_streak(active_dates)

    active_days = len(active_dates)

    # Tipos de tarea (desde payload JSON o nombre de task)
    type_rows = await db.execute(
        select(Task.payload, Task.name)
        .join(Result, Result.task_id == Task.id)
        .where(Task.user_id == current_user.id)
    )
    task_types_set: set[str] = set()
    for payload, name in type_rows.all():
        t = None
        if isinstance(payload, str):
            try:
                import json
                data = json.loads(payload)
                t = data.get("type")
            except Exception:
                pass
        elif isinstance(payload, dict):
            t = payload.get("type")
        if not t and name:
            # fallback: posidonia-auto-... → posidonia
            t = str(name).split("-")[0].lower()
        if t:
            task_types_set.add(str(t).lower())
    task_types = sorted(task_types_set)

    level = compute_level(tasks_done, active_days, streak_days, task_types)
    achievements = compute_achievements(
        tasks_done, streak_days, task_types, last_active_at
    )

    return CreditsSummary(
        user_id=current_user.id,
        username=current_user.username,
        total=total,
        recent=[CreditOut.model_validate(c, from_attributes=True) for c in recent],
        by_mode=by_mode,
        by_client=by_client,
        tasks_done=tasks_done,
        credits_this_week=credits_this_week,
        streak_days=streak_days,
        last_active_at=last_active_at,
        active_days=active_days,
        task_types=task_types,
        level=level,
        achievements=achievements,
    )
