"""Asigna hexágono de impacto al completar una tarea con coordenadas."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserImpactHex
from app.services.impact_geo import bbox_centroid, payload_to_hex


async def try_assign_hex_from_task(
    db: AsyncSession,
    *,
    user_id: int,
    task_payload: dict | str | None,
    tile_slug: str = "arctic",
    color: str = "glacier",
) -> Optional[UserImpactHex]:
    """
    Si el payload tiene bbox cuyo centroide cae en la loseta,
    crea UserImpactHex (idempotente: no duplica).
    Devuelve el hex creado o None.
    """
    if isinstance(task_payload, str):
        try:
            payload: dict[str, Any] = json.loads(task_payload)
        except Exception:
            return None
    elif isinstance(task_payload, dict):
        payload = task_payload
    else:
        return None

    hex_code = payload_to_hex(payload, tile_slug=tile_slug)
    if not hex_code:
        return None

    existing = await db.execute(
        select(UserImpactHex).where(
            UserImpactHex.user_id == user_id,
            UserImpactHex.tile_slug == tile_slug,
            UserImpactHex.hex_code == hex_code,
        )
    )
    if existing.scalar_one_or_none():
        return None

    bbox = payload.get("bbox")
    if not bbox:
        aoi = payload.get("aoi") or payload.get("geometry") or {}
        bbox = aoi.get("bbox") if isinstance(aoi, dict) else None
    centroid = bbox_centroid(bbox) if bbox else None
    lat = centroid[0] if centroid else None
    lon = centroid[1] if centroid else None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    row = UserImpactHex(
        user_id=user_id,
        tile_slug=tile_slug,
        hex_code=hex_code,
        color=color,
        source="task_geo",
        expedition_slug=None,
        lat=lat,
        lon=lon,
        unlocked_at=now,
        validated_at=None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
