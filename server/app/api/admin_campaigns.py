"""Gestión de campañas (expediciones) desde el panel admin. Solo superadmin.

Una campaña se crea siempre como BORRADOR (is_active = False). Publicarla es un
paso aparte. Estados que se calculan:

  completed  completada (alcanzó su meta)
  paused     no publicada (borrador o pausada)
  scheduled  publicada, pero aún no ha empezado
  ended      publicada, pero ya pasó su fecha de fin
  running    publicada, dentro de fechas y sin completar
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_superadmin
from app.db.database import get_db
from app.db.models import Expedition, ExpeditionParticipant, Task, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/campaigns", tags=["admin"])

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
THEME_RE = re.compile(r"^[a-z0-9_]{1,40}$")

# Tipos de tarea que saben calcular los clientes y validar el servidor
TASK_TYPES = {"ndvi", "posidonia", "biodiversity"}

# Marcos de recompensa que ya viajan dentro de la GUI y la APK
# (assets/frames). Un marco nuevo exige publicar clientes nuevos.
ALLOWED_FRAMES = {
    "arctic_ice", "autumn_fungi", "deforestation", "energy",
    "environmental_crime", "ozone", "posidonia", "sea_ice", "water",
}


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _naive_utc(dt: datetime) -> datetime:
    """Las fechas se guardan en UTC y sin zona horaria."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _status(e: Expedition, now: datetime) -> str:
    if e.completed_at is not None:
        return "completed"
    if not e.is_active:
        return "paused"
    if now < e.starts_at:
        return "scheduled"
    if now > e.ends_at:
        return "ended"
    return "running"


def _check_choices(
    task_type: str | None, theme: str | None, reward_frame: str | None
) -> None:
    if task_type is not None and task_type not in TASK_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de tarea no válido. Opciones: {', '.join(sorted(TASK_TYPES))}",
        )
    if theme is not None and not THEME_RE.match(theme):
        raise HTTPException(
            status_code=400,
            detail="La temática solo admite minúsculas, números y guion bajo (máx. 40)",
        )
    if reward_frame is not None and reward_frame not in ALLOWED_FRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Marco no disponible en los clientes. Opciones: {', '.join(sorted(ALLOWED_FRAMES))}",
        )


async def _participants_map(db: AsyncSession) -> dict[int, int]:
    rows = (
        await db.execute(
            select(ExpeditionParticipant.expedition_id, func.count())
            .group_by(ExpeditionParticipant.expedition_id)
        )
    ).all()
    return {eid: n for eid, n in rows}


async def _queue_map(db: AsyncSession) -> tuple[dict[str | None, int], int]:
    """Tareas pendientes por temática, y el total."""
    rows = (
        await db.execute(
            select(Task.theme, func.count())
            .where(Task.status == "pending")
            .group_by(Task.theme)
        )
    ).all()
    by_theme = {theme: n for theme, n in rows}
    return by_theme, sum(by_theme.values())


def _serialize(
    e: Expedition,
    now: datetime,
    participants: dict[int, int],
    queue_by_theme: dict[str | None, int],
    queue_total: int,
) -> dict:
    goal = max(e.goal_value, 1)
    return {
        "id": e.id,
        "slug": e.slug,
        "name": e.name,
        "description": e.description,
        "task_type": e.task_type,
        "theme": e.theme,
        "tile_slug": e.tile_slug,
        "goal_value": e.goal_value,
        "current_value": e.current_value,
        "progress": min(e.current_value / goal, 1.0),
        "reward_frame": e.reward_frame,
        "reward_badge_id": e.reward_badge_id,
        "starts_at": _iso(e.starts_at),
        "ends_at": _iso(e.ends_at),
        "completed_at": _iso(e.completed_at),
        "is_active": e.is_active,
        "status": _status(e, now),
        "participants": participants.get(e.id, 0),
        # Sin temática, la campaña cuenta cualquier tarea: se muestra el total
        "queue_pending": queue_by_theme.get(e.theme, 0) if e.theme else queue_total,
    }


async def _serialize_one(db: AsyncSession, e: Expedition) -> dict:
    await db.refresh(e)
    by_theme, total = await _queue_map(db)
    return _serialize(e, _now(), await _participants_map(db), by_theme, total)


async def _get_or_404(db: AsyncSession, campaign_id: int) -> Expedition:
    e = await db.get(Expedition, campaign_id)
    if not e:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return e


# ------------------------------------------------------------------ listado

@router.get("")
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    now = _now()
    rows = (
        await db.execute(select(Expedition).order_by(Expedition.starts_at.desc()))
    ).scalars().all()
    participants = await _participants_map(db)
    by_theme, total = await _queue_map(db)
    return {
        "campaigns": [_serialize(e, now, participants, by_theme, total) for e in rows],
        "options": {
            "task_types": sorted(TASK_TYPES),
            "reward_frames": sorted(ALLOWED_FRAMES),
        },
    }


# ------------------------------------------------------------------- crear

class CampaignCreate(BaseModel):
    slug: str = Field(min_length=3, max_length=40)
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    task_type: str | None = None   # ndvi | posidonia | biodiversity | None = cualquiera
    theme: str | None = None       # prefijo/etiqueta de las tareas de la campaña
    tile_slug: str | None = Field(default=None, max_length=40)
    goal_value: int = Field(ge=1, le=10_000_000)
    reward_frame: str | None = None
    reward_badge_id: str | None = Field(default=None, max_length=40)
    starts_at: datetime
    ends_at: datetime


@router.post("", status_code=201)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    """Crea una campaña como borrador (no publicada)."""
    if not SLUG_RE.match(payload.slug):
        raise HTTPException(
            status_code=400,
            detail="El identificador solo admite minúsculas, números y guiones (p. ej. spring-posidonia-2027)",
        )
    _check_choices(payload.task_type, payload.theme, payload.reward_frame)

    starts_at = _naive_utc(payload.starts_at)
    ends_at = _naive_utc(payload.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio")

    exists = (
        await db.execute(select(Expedition.id).where(Expedition.slug == payload.slug).limit(1))
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="Ya existe una campaña con ese identificador")

    admin_username = admin.username
    campaign = Expedition(
        slug=payload.slug,
        name=payload.name.strip(),
        description=payload.description,
        task_type=payload.task_type,
        theme=payload.theme,
        tile_slug=payload.tile_slug,
        goal_value=payload.goal_value,
        current_value=0,
        reward_frame=payload.reward_frame,
        reward_badge_id=payload.reward_badge_id,
        starts_at=starts_at,
        ends_at=ends_at,
        is_active=False,
    )
    db.add(campaign)
    await db.commit()
    logger.info("Campaña %s creada (borrador) por %s", payload.slug, admin_username)
    return await _serialize_one(db, campaign)


# ------------------------------------------------------------------ editar

class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    task_type: str | None = None
    theme: str | None = None
    tile_slug: str | None = Field(default=None, max_length=40)
    goal_value: int | None = Field(default=None, ge=1, le=10_000_000)
    reward_frame: str | None = None
    reward_badge_id: str | None = Field(default=None, max_length=40)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


# La temática, el tipo y la loseta cambian lo que cuenta la campaña: solo antes de que tenga progreso
_LOCKED_AFTER_PROGRESS = {"task_type", "theme", "tile_slug"}


@router.patch("/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    campaign = await _get_or_404(db, campaign_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No hay cambios que aplicar")

    if campaign.current_value > 0 and _LOCKED_AFTER_PROGRESS & changes.keys():
        raise HTTPException(
            status_code=409,
            detail="El tipo de tarea, la temática y la loseta no se pueden cambiar cuando la campaña ya tiene progreso",
        )
    _check_choices(changes.get("task_type"), changes.get("theme"), changes.get("reward_frame"))

    for key in ("starts_at", "ends_at"):
        if changes.get(key) is not None:
            changes[key] = _naive_utc(changes[key])
    starts_at = changes.get("starts_at", campaign.starts_at)
    ends_at = changes.get("ends_at", campaign.ends_at)
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="La fecha de fin debe ser posterior a la de inicio")

    if "name" in changes and changes["name"] is not None:
        changes["name"] = changes["name"].strip()
    if "goal_value" in changes and changes["goal_value"] is None:
        changes.pop("goal_value")

    admin_username = admin.username
    slug = campaign.slug
    for key, value in changes.items():
        setattr(campaign, key, value)
    await db.commit()
    logger.info("Campaña %s editada por %s: %s", slug, admin_username, sorted(changes))
    return await _serialize_one(db, campaign)


# --------------------------------------------------- publicar, pausar, reabrir

@router.post("/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    campaign = await _get_or_404(db, campaign_id)
    if campaign.completed_at is not None:
        raise HTTPException(status_code=400, detail="La campaña está completada: reábrela primero con una meta mayor")
    if campaign.ends_at < _now():
        raise HTTPException(status_code=400, detail="La fecha de fin ya pasó: edítala antes de publicar")

    admin_username = admin.username
    slug = campaign.slug
    campaign.is_active = True
    await db.commit()
    logger.info("Campaña %s publicada por %s", slug, admin_username)
    return await _serialize_one(db, campaign)


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    campaign = await _get_or_404(db, campaign_id)
    admin_username = admin.username
    slug = campaign.slug
    campaign.is_active = False
    await db.commit()
    logger.info("Campaña %s pausada por %s", slug, admin_username)
    return await _serialize_one(db, campaign)


class ReopenIn(BaseModel):
    goal_value: int = Field(ge=1, le=10_000_000)
    ends_at: datetime | None = None


@router.post("/{campaign_id}/reopen")
async def reopen_campaign(
    campaign_id: int,
    payload: ReopenIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    """Reabre una campaña completada con una meta mayor. No retira marcos ya otorgados."""
    campaign = await _get_or_404(db, campaign_id)
    if campaign.completed_at is None:
        raise HTTPException(status_code=400, detail="La campaña no está completada")
    if payload.goal_value <= campaign.current_value:
        raise HTTPException(
            status_code=400,
            detail=f"La nueva meta debe ser mayor que el progreso actual ({campaign.current_value})",
        )

    new_end = _naive_utc(payload.ends_at) if payload.ends_at else campaign.ends_at
    if new_end < _now():
        raise HTTPException(status_code=400, detail="La fecha de fin ya pasó: indica una nueva")

    admin_username = admin.username
    slug = campaign.slug
    campaign.goal_value = payload.goal_value
    campaign.ends_at = new_end
    campaign.completed_at = None
    await db.commit()
    logger.info("Campaña %s reabierta por %s con meta %s", slug, admin_username, payload.goal_value)
    return await _serialize_one(db, campaign)
