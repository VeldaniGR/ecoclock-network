from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import Expedition
from app.schemas.expedition import ExpeditionOut

router = APIRouter()


def _to_out(e: Expedition) -> ExpeditionOut:
    goal = max(e.goal_value, 1)
    progress = min(e.current_value / goal, 1.0)
    return ExpeditionOut(
        id=e.id,
        slug=e.slug,
        name=e.name,
        description=e.description,
        task_type=e.task_type,
        goal_value=e.goal_value,
        current_value=e.current_value,
        progress=progress,
        reward_frame=e.reward_frame,
        reward_badge_id=e.reward_badge_id,
        starts_at=e.starts_at,
        ends_at=e.ends_at,
        completed_at=e.completed_at,
        is_active=e.is_active,
        is_completed=e.completed_at is not None or e.current_value >= e.goal_value,
    )


@router.get("/current", response_model=ExpeditionOut | None)
async def get_current_expedition(db: AsyncSession = Depends(get_db)):
    """Expedición activa en este momento (público)."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = await db.execute(
        select(Expedition)
        .where(
            Expedition.is_active == True,  # noqa: E712
            Expedition.starts_at <= now,
            Expedition.ends_at >= now,
        )
        .order_by(Expedition.starts_at.desc())
        .limit(1)
    )
    e = result.scalar_one_or_none()
    if not e:
        return None
    return _to_out(e)


@router.get("/", response_model=list[ExpeditionOut])
async def list_expeditions(db: AsyncSession = Depends(get_db)):
    """Listado de expediciones (público)."""
    result = await db.execute(select(Expedition).order_by(Expedition.starts_at.desc()))
    return [_to_out(e) for e in result.scalars().all()]


# ---------------------------------------------------------------------------
# Endpoints personales de expedición (claim + submit-photo)
# ---------------------------------------------------------------------------

from app.api.auth import get_current_user
from app.db.models import User, UserImpactHex
from app.schemas.impact import ClaimExpeditionOut, ImpactHexOut, SubmitPhotoOut


@router.post("/{slug}/claim", response_model=ClaimExpeditionOut)
async def claim_expedition(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reclama una expedición (marca como claimed).
    Por ahora NO asigna hexágono de forma inteligente (se hará más adelante
    con coordenadas reales de las tareas). Solo registra el claim.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Verificar que la expedición existe y está activa
    result = await db.execute(
        select(Expedition).where(Expedition.slug == slug)
    )
    expedition = result.scalar_one_or_none()
    if not expedition:
        raise HTTPException(status_code=404, detail="Expedición no encontrada")
    if not expedition.is_active:
        raise HTTPException(status_code=400, detail="Expedición no activa")
    if expedition.starts_at > now or expedition.ends_at < now:
        raise HTTPException(status_code=400, detail="Expedición fuera de fechas")

    # TODO: aquí irá la lógica inteligente de asignación de hexágono
    # por coordenadas de tareas reales. De momento devolvemos sin hex.

    return ClaimExpeditionOut(
        expedition_slug=slug,
        status="claimed",
        assigned_hex=None,
        message=(
            "Expedición reclamada. "
            "La asignación de hexágono por coordenadas se activará en una próxima versión."
        ),
    )


@router.post("/{slug}/submit-photo", response_model=SubmitPhotoOut)
async def submit_photo(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registra que el usuario ha enviado la foto de la actividad exterior.
    (La validación real se hace manualmente / por admin de momento.)
    """
    result = await db.execute(
        select(Expedition).where(Expedition.slug == slug)
    )
    expedition = result.scalar_one_or_none()
    if not expedition:
        raise HTTPException(status_code=404, detail="Expedición no encontrada")

    # Por ahora solo confirmamos la recepción.
    # Más adelante: crear/actualizar UserImpactHex con validated_at = None
    # y un estado "submitted".

    return SubmitPhotoOut(
        expedition_slug=slug,
        status="submitted",
        message=(
            "Foto registrada. "
            "Cuando el equipo la valide recibirás el hexágono y el logro."
        ),
    )
