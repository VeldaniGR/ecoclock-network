"""Validación manual de la actividad exterior (Sobre de navegante) desde el panel admin.

Tres operaciones, todas solo para superadmin:
  - listar los sobres (pendientes de validar o ya validados),
  - ver el mapa de un usuario con los hexágonos libres,
  - validar un sobre eligiendo en qué hexágono libre se otorga el dorado.

La lógica de otorgar el hexágono la sigue haciendo el servicio que ya existe
(app.services.navigator_envelope.validate_envelope). Aquí solo se comprueba que
el hexágono elegido sea válido y esté libre antes de llamarlo.
"""
from __future__ import annotations

import logging
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_superadmin
from app.db.database import get_db
from app.db.models import NavigatorEnvelope, User, UserImpactHex

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/validation", tags=["admin"])

# Rejilla del mapa: de A1 a J10 (igual que la GUI y la APK)
COLS = 10
ROWS = 10
_HEX_RE = re.compile(r"^([A-Z])(\d{1,2})$")


def _normalize_hex(code: str | None) -> str | None:
    """'b7' -> 'B7'. Devuelve None si no es un hexágono de la rejilla."""
    match = _HEX_RE.match((code or "").strip().upper())
    if not match:
        return None
    row = ord(match.group(1)) - ord("A")
    col = int(match.group(2))
    if row >= ROWS or not 1 <= col <= COLS:
        return None
    return f"{match.group(1)}{col}"


def _all_codes() -> list[str]:
    return [f"{chr(ord('A') + r)}{c}" for r in range(ROWS) for c in range(1, COLS + 1)]


def _iso(value) -> str | None:
    return value.isoformat() if value else None


# --------------------------------------------------------------- listado

@router.get("/envelopes")
async def list_envelopes(
    status: Literal["pending", "validated", "all"] = "pending",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Sobres de navegante. 'pending' = todavía sin validar."""
    query = (
        select(NavigatorEnvelope, User.username, User.email)
        .join(User, User.id == NavigatorEnvelope.user_id)
        .order_by(NavigatorEnvelope.ready_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status == "pending":
        query = query.where(NavigatorEnvelope.validated_at.is_(None))
    elif status == "validated":
        query = query.where(NavigatorEnvelope.validated_at.is_not(None))

    rows = (await db.execute(query)).all()
    return {
        "envelopes": [
            {
                "id": env.id,
                "user_id": env.user_id,
                "username": username,
                "email": email,
                "expedition_slug": env.expedition_slug,
                "tile_slug": env.tile_slug,
                "status": env.status,
                "hex_count_at_ready": env.hex_count_at_ready,
                "task_count_at_ready": env.task_count_at_ready,
                "ready_at": _iso(env.ready_at),
                "sent_at": _iso(env.sent_at),
                "validated_at": _iso(env.validated_at),
            }
            for env, username, email in rows
        ]
    }


# ------------------------------------------------------- mapa de un usuario

@router.get("/users/{user_id}/map")
async def get_user_map(
    user_id: int,
    tile: str = Query("arctic", max_length=40),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_superadmin),
):
    """Hexágonos de un usuario y los códigos que aún están libres (candidatos al dorado)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    hexes = (
        await db.execute(
            select(UserImpactHex)
            .where(UserImpactHex.user_id == user_id)
            .where(UserImpactHex.tile_slug == tile)
            .order_by(UserImpactHex.unlocked_at.asc())
        )
    ).scalars().all()

    owned = {(h.hex_code or "").upper() for h in hexes}
    return {
        "user": {"id": user.id, "username": user.username, "email": user.email},
        "tile": tile,
        "total_hexes": len(hexes),
        "hexes": [
            {
                "hex_code": h.hex_code,
                "color": h.color,
                "source": h.source,
                "unlocked_at": _iso(h.unlocked_at),
                "validated_at": _iso(h.validated_at),
            }
            for h in hexes
        ],
        "free_codes": [c for c in _all_codes() if c not in owned],
    }


# ---------------------------------------------------------------- validar

class ValidateIn(BaseModel):
    # Hexágono libre donde otorgar el dorado. Sin valor, decide el servicio.
    hex_code: str | None = Field(default=None, max_length=10)


@router.post("/envelopes/{envelope_id}/validate")
async def validate_envelope_from_panel(
    envelope_id: int,
    payload: ValidateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_superadmin),
):
    """Marca el sobre como validado y otorga el hexágono dorado en el elegido."""
    envelope = await db.get(NavigatorEnvelope, envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail="Sobre no encontrado")
    if envelope.validated_at is not None or envelope.status == "validated":
        raise HTTPException(status_code=409, detail="Este sobre ya está validado")

    user_id = envelope.user_id
    expedition_slug = envelope.expedition_slug
    tile_slug = envelope.tile_slug
    admin_username = admin.username

    hex_code = None
    if payload.hex_code and payload.hex_code.strip():
        hex_code = _normalize_hex(payload.hex_code)
        if hex_code is None:
            raise HTTPException(
                status_code=400,
                detail=f"Hexágono no válido (de A1 a {chr(ord('A') + ROWS - 1)}{COLS})",
            )
        taken = (
            await db.execute(
                select(UserImpactHex.id)
                .where(UserImpactHex.user_id == user_id)
                .where(UserImpactHex.tile_slug == tile_slug)
                .where(func.upper(UserImpactHex.hex_code) == hex_code)
                .limit(1)
            )
        ).first()
        if taken:
            raise HTTPException(status_code=409, detail="El usuario ya tiene ese hexágono")

    from app.services.navigator_envelope import validate_envelope

    try:
        data = await validate_envelope(
            db, user_id, expedition_slug=expedition_slug, hex_code=hex_code
        )
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        await db.rollback()
        logger.exception("Fallo al validar el sobre %s", envelope_id)
        raise HTTPException(status_code=500, detail="No se pudo validar el sobre")

    logger.info(
        "Sobre %s del usuario %s validado por %s (hexágono %s)",
        envelope_id, user_id, admin_username, hex_code or "automático",
    )
    return data
