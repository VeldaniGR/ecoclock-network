"""Schemas Pydantic para el mapa de impacto y hexágonos."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ImpactHexOut(BaseModel):
    """Un hexágono desbloqueado por el usuario."""
    tile_slug: str
    hex_code: str
    color: str
    source: str
    expedition_slug: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    unlocked_at: datetime
    validated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ImpactTileSummaryOut(BaseModel):
    """Resumen de una loseta con sus hexágonos."""
    tile_slug: str
    tile_name: Optional[str] = None
    total_unlocked: int
    hexes: List[ImpactHexOut]


class MeImpactOut(BaseModel):
    """Respuesta de GET /me/impact."""
    tiles: List[ImpactTileSummaryOut]
    total_hexes: int = 0


class ClaimExpeditionOut(BaseModel):
    """Respuesta de POST /me/expeditions/{slug}/claim."""
    expedition_slug: str
    status: str  # "claimed"
    assigned_hex: Optional[ImpactHexOut] = None
    message: str


class SubmitPhotoOut(BaseModel):
    """Respuesta de POST /me/expeditions/{slug}/submit-photo."""
    expedition_slug: str
    status: str  # "submitted"
    message: str


# --- Opcional: para listar losetas ---

class ImpactTileOut(BaseModel):
    slug: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class NavigatorEnvelopeOut(BaseModel):
    """Estado del Sobre de navegante (5 hex / 25 tareas)."""
    status: str  # locked | ready | sent | validated
    expedition_slug: Optional[str] = None
    tile_slug: str = "arctic"
    hex_count: int = 0
    hex_threshold: int = 5
    personal_task_count: int = 0
    task_threshold: int = 25
    message: Optional[str] = None
    trigger: Optional[str] = None

