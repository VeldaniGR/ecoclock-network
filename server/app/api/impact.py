"""Endpoints del mapa de impacto (hexágonos personales) y sobre de navegante."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import ImpactTile, User, UserImpactHex
from app.schemas.impact import (
    ImpactHexOut,
    ImpactTileSummaryOut,
    MeImpactOut,
    NavigatorEnvelopeOut,
)

router = APIRouter(prefix="/me/impact", tags=["impact"])


@router.get("", response_model=MeImpactOut)
async def get_my_impact(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve todos los hexágonos desbloqueados del usuario, agrupados por loseta."""
    result = await db.execute(
        select(UserImpactHex)
        .where(UserImpactHex.user_id == current_user.id)
        .order_by(UserImpactHex.unlocked_at.asc())
    )
    hexes = result.scalars().all()

    by_tile: dict[str, list[UserImpactHex]] = defaultdict(list)
    for h in hexes:
        by_tile[h.tile_slug].append(h)

    tile_names: dict[str, str] = {}
    if by_tile:
        tiles_result = await db.execute(
            select(ImpactTile).where(ImpactTile.slug.in_(list(by_tile.keys())))
        )
        for t in tiles_result.scalars().all():
            tile_names[t.slug] = t.name

    summaries: list[ImpactTileSummaryOut] = []
    total = 0
    for slug, hex_list in by_tile.items():
        out_hexes = [ImpactHexOut.model_validate(h) for h in hex_list]
        summaries.append(
            ImpactTileSummaryOut(
                tile_slug=slug,
                tile_name=tile_names.get(slug),
                total_unlocked=len(out_hexes),
                hexes=out_hexes,
            )
        )
        total += len(out_hexes)

    return MeImpactOut(tiles=summaries, total_hexes=total)


# ---------------------------------------------------------------------------
# Sobre de navegante (DEBE ir ANTES de /{tile_slug})
# ---------------------------------------------------------------------------

@router.get("/navigator-envelope", response_model=NavigatorEnvelopeOut)
async def get_navigator_envelope(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estado del Sobre de navegante (5 hex / 25 tareas personales)."""
    from app.services.navigator_envelope import get_envelope_state

    data = await get_envelope_state(db, current_user.id)
    return NavigatorEnvelopeOut(**data)


@router.post("/navigator-envelope/ack-sent", response_model=NavigatorEnvelopeOut)
async def ack_navigator_envelope_sent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirma que el usuario ha solicitado / recibido el correo del sobre."""
    from app.services.navigator_envelope import get_envelope_state, mark_envelope_sent

    state = await get_envelope_state(db, current_user.id)
    slug = state.get("expedition_slug")
    if not slug:
        return NavigatorEnvelopeOut(**state)
    data = await mark_envelope_sent(db, current_user.id, slug)
    return NavigatorEnvelopeOut(**data)


# ---------------------------------------------------------------------------
# Loseta concreta (ruta genérica: la última)
# ---------------------------------------------------------------------------

@router.get("/{tile_slug}", response_model=ImpactTileSummaryOut)
async def get_my_impact_tile(
    tile_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hexágonos del usuario en una loseta concreta."""
    result = await db.execute(
        select(UserImpactHex)
        .where(
            UserImpactHex.user_id == current_user.id,
            UserImpactHex.tile_slug == tile_slug,
        )
        .order_by(UserImpactHex.unlocked_at.asc())
    )
    hexes = result.scalars().all()

    tile_name = None
    tile_result = await db.execute(
        select(ImpactTile).where(ImpactTile.slug == tile_slug)
    )
    tile = tile_result.scalar_one_or_none()
    if tile:
        tile_name = tile.name

    out_hexes = [ImpactHexOut.model_validate(h) for h in hexes]
    return ImpactTileSummaryOut(
        tile_slug=tile_slug,
        tile_name=tile_name,
        total_unlocked=len(out_hexes),
        hexes=out_hexes,
    )
