"""Mapa de impacto colectivo: hexágonos agregados por nodo y por red.

Solo devuelve recuentos: para cada hexágono, cuántos participantes lo han
desbloqueado. No expone nombres ni identificadores de otros usuarios.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.db.models import Node, NodeMember, User, UserImpactHex

router = APIRouter(prefix="/impact", tags=["impact"])

DEFAULT_TILE = "arctic"


async def _aggregate_hexes(db: AsyncSession, tile_slug: str, user_ids=None) -> list[dict]:
    """Hexágonos desbloqueados de una loseta, con el nº de participantes de cada uno.

    user_ids: subconsulta con los usuarios a incluir (None = todos).
    El color de cada hexágono es el de su desbloqueo más reciente.
    """
    counts_q = (
        select(
            UserImpactHex.hex_code,
            func.count(func.distinct(UserImpactHex.user_id)).label("n"),
        )
        .where(UserImpactHex.tile_slug == tile_slug)
        .group_by(UserImpactHex.hex_code)
    )
    latest_q = (
        select(UserImpactHex.hex_code, UserImpactHex.color, UserImpactHex.unlocked_at)
        .where(UserImpactHex.tile_slug == tile_slug)
        .distinct(UserImpactHex.hex_code)  # DISTINCT ON de PostgreSQL
        .order_by(UserImpactHex.hex_code, UserImpactHex.unlocked_at.desc())
    )
    if user_ids is not None:
        counts_q = counts_q.where(UserImpactHex.user_id.in_(user_ids))
        latest_q = latest_q.where(UserImpactHex.user_id.in_(user_ids))

    counts = {code: n for code, n in (await db.execute(counts_q)).all()}
    hexes = [
        {
            "hex_code": code,
            "color": color,
            "count": counts.get(code, 1),
            "unlocked_at": at.isoformat() if at else None,
        }
        for code, color, at in (await db.execute(latest_q)).all()
    ]
    hexes.sort(key=lambda h: h["hex_code"])
    return hexes


@router.get("/node")
async def get_node_impact(
    tile: str = Query(DEFAULT_TILE, max_length=40),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hexágonos del nodo del usuario. `participants` = miembros del nodo."""
    row = (
        await db.execute(
            select(Node.id, Node.name)
            .join(NodeMember, NodeMember.node_id == Node.id)
            .where(NodeMember.user_id == current_user.id)
            .order_by(NodeMember.id.asc())
            .limit(1)
        )
    ).first()
    if not row:
        return {"node": None, "participants": 0, "total_hexes": 0, "hexes": []}

    node_id, node_name = row
    members = select(NodeMember.user_id).where(NodeMember.node_id == node_id)
    hexes = await _aggregate_hexes(db, tile, members)
    participants = (
        await db.execute(
            select(func.count(func.distinct(NodeMember.user_id))).where(
                NodeMember.node_id == node_id
            )
        )
    ).scalar_one()

    return {
        "node": {"id": node_id, "name": node_name},
        "participants": participants,
        "total_hexes": len(hexes),
        "hexes": hexes,
    }


@router.get("/network")
async def get_network_impact(
    tile: str = Query(DEFAULT_TILE, max_length=40),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Hexágonos de toda la red. `participants` = usuarios con al menos un hexágono."""
    hexes = await _aggregate_hexes(db, tile)
    participants = (
        await db.execute(
            select(func.count(func.distinct(UserImpactHex.user_id))).where(
                UserImpactHex.tile_slug == tile
            )
        )
    ).scalar_one()

    return {
        "participants": participants,
        "total_hexes": len(hexes),
        "hexes": hexes,
    }
