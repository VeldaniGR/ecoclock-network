"""Elegibilidad del Sobre de navegante (5 hexágonos / 25 tareas personales)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Credit, Expedition, NavigatorEnvelope, Task, UserImpactHex

HEX_THRESHOLD = 5
TASK_THRESHOLD = 25
DEFAULT_TILE = "arctic"


async def _active_arctic_expedition(db: AsyncSession) -> Expedition | None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Expedition)
        .where(
            Expedition.is_active == True,  # noqa: E712
            Expedition.starts_at <= now,
            Expedition.ends_at >= now,
        )
        .order_by(Expedition.starts_at.desc())
    )
    rows = list(result.scalars().all())
    for e in rows:
        slug = (e.slug or "").lower()
        name = (e.name or "").lower()
        if "arctic" in slug or "winter" in slug or "hielo" in name or "artico" in name:
            return e
    return rows[0] if rows else None


async def count_hexes(
    db: AsyncSession, user_id: int, tile_slug: str = DEFAULT_TILE
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UserImpactHex)
        .where(
            UserImpactHex.user_id == user_id,
            UserImpactHex.tile_slug == tile_slug,
        )
    )
    return int(result.scalar_one() or 0)


async def count_personal_tasks_in_window(
    db: AsyncSession,
    user_id: int,
    starts_at: datetime,
    ends_at: datetime,
) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Credit)
        .where(
            Credit.user_id == user_id,
            Credit.granted_at >= starts_at,
            Credit.granted_at <= ends_at,
        )
    )
    return int(result.scalar_one() or 0)


async def get_envelope_state(db: AsyncSession, user_id: int) -> dict[str, Any]:
    exp = await _active_arctic_expedition(db)
    hex_count = await count_hexes(db, user_id, DEFAULT_TILE)

    if not exp:
        return {
            "status": "locked",
            "expedition_slug": None,
            "tile_slug": DEFAULT_TILE,
            "hex_count": hex_count,
            "hex_threshold": HEX_THRESHOLD,
            "personal_task_count": 0,
            "task_threshold": TASK_THRESHOLD,
            "message": None,
            "trigger": None,
        }

    task_count = await count_personal_tasks_in_window(
        db, user_id, exp.starts_at, exp.ends_at
    )

    result = await db.execute(
        select(NavigatorEnvelope).where(
            NavigatorEnvelope.user_id == user_id,
            NavigatorEnvelope.expedition_slug == exp.slug,
        )
    )
    row = result.scalar_one_or_none()

    if row and row.status in ("sent", "validated"):
        status = row.status
        trigger = row.trigger
    elif hex_count >= HEX_THRESHOLD or task_count >= TASK_THRESHOLD:
        trigger = "hexes" if hex_count >= HEX_THRESHOLD else "tasks"
        if row is None:
            row = NavigatorEnvelope(
                user_id=user_id,
                expedition_slug=exp.slug,
                tile_slug=DEFAULT_TILE,
                status="ready",
                trigger=trigger,
                hex_count_at_ready=hex_count,
                task_count_at_ready=task_count,
            )
            db.add(row)
            await db.commit()
            await db.refresh(row)
        elif row.status not in ("sent", "validated"):
            row.status = "ready"
            row.trigger = trigger
            await db.commit()
        status = "ready"
        trigger = row.trigger
    else:
        status = "locked"
        trigger = None

    message = None
    if status == "ready":
        message = "Tu sobre de navegante está listo"
    elif status == "sent":
        message = "Sobre enviado — completa la actividad exterior"
    elif status == "validated":
        message = "Actividad exterior validada — ¡Navegante del hielo!"

    return {
        "status": status,
        "expedition_slug": exp.slug,
        "tile_slug": DEFAULT_TILE,
        "hex_count": hex_count,
        "hex_threshold": HEX_THRESHOLD,
        "personal_task_count": task_count,
        "task_threshold": TASK_THRESHOLD,
        "message": message,
        "trigger": trigger,
    }


async def mark_envelope_sent(
    db: AsyncSession, user_id: int, expedition_slug: str
) -> dict[str, Any]:
    state = await get_envelope_state(db, user_id)
    if state.get("status") not in ("ready", "sent"):
        return state

    result = await db.execute(
        select(NavigatorEnvelope).where(
            NavigatorEnvelope.user_id == user_id,
            NavigatorEnvelope.expedition_slug == expedition_slug,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        row.status = "sent"
        row.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
    return await get_envelope_state(db, user_id)
