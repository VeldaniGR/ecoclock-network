"""
Asignación de hexágonos del mapa de impacto a partir de coordenadas.

Diseño v1 – loseta Ártico (proyección simple por lat/lon):
- Definimos un bounding box del Ártico.
- Lo dividimos en una rejilla axial de hexágonos (estilo Catan / flat-top).
- Dado un punto (lat, lon) devolvemos el código del hexágono (A1, B3…).

Más adelante se puede sustituir por una proyección polar real
sin cambiar la interfaz pública.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Configuración de la loseta Ártico
# ---------------------------------------------------------------------------

# Bounding box aproximado del Ártico (EPSG:4326)
# Ajustable: cubre ~60°N hacia el polo, circunpolar simplificado
ARCTIC_BBOX = {
    "min_lon": -180.0,
    "max_lon":  180.0,
    "min_lat":   60.0,   # círculo polar ártico ~66.5°, usamos 60° para margen
    "max_lat":   90.0,
}

# Rejilla: filas (letras) × columnas (números)
# Debe coincidir con la loseta PDF (10 columnas × 10–11 filas)
GRID_COLS = 10
GRID_ROWS = 10
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def point_in_arctic(lat: float, lon: float) -> bool:
    """True si el punto cae dentro del bbox de la loseta Ártico."""
    b = ARCTIC_BBOX
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]


def latlon_to_hex(lat: float, lon: float) -> Optional[str]:
    """
    Convierte (lat, lon) en código de hexágono de la loseta Ártico.

    Retorna None si el punto está fuera del bbox.
    """
    if not point_in_arctic(lat, lon):
        return None

    b = ARCTIC_BBOX
    # Normalizar a [0, 1]
    x = (lon - b["min_lon"]) / (b["max_lon"] - b["min_lon"])  # 0 = oeste, 1 = este
    y = (b["max_lat"] - lat) / (b["max_lat"] - b["min_lat"])  # 0 = norte, 1 = sur

    x = _clamp(x, 0.0, 0.9999)
    y = _clamp(y, 0.0, 0.9999)

    col = int(x * GRID_COLS) + 1          # 1..GRID_COLS
    row = int(y * GRID_ROWS)              # 0..GRID_ROWS-1

    if row >= len(LETTERS):
        row = len(LETTERS) - 1

    return f"{LETTERS[row]}{col}"


def bbox_centroid(bbox: dict) -> Optional[Tuple[float, float]]:
    """
    Extrae el centroide de un bbox de tarea.
    Acepta tanto {"min_lon", "min_lat", "max_lon", "max_lat"}
    como lista [min_lon, min_lat, max_lon, max_lat].
    """
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        min_lon, min_lat, max_lon, max_lat = bbox
    elif isinstance(bbox, dict):
        try:
            min_lon = float(bbox["min_lon"])
            min_lat = float(bbox["min_lat"])
            max_lon = float(bbox["max_lon"])
            max_lat = float(bbox["max_lat"])
        except (KeyError, TypeError, ValueError):
            return None
    else:
        return None

    lat = (min_lat + max_lat) / 2.0
    lon = (min_lon + max_lon) / 2.0
    return lat, lon


def payload_to_hex(payload: dict, tile_slug: str = "arctic") -> Optional[str]:
    """
    Dado el payload JSON de una tarea, devuelve el hex_code de la loseta
    si el centroide cae dentro. Por ahora solo implementamos 'arctic'.
    """
    if tile_slug != "arctic":
        return None

    bbox = payload.get("bbox")
    if not bbox:
        # Algunos payloads anidan el bbox dentro de "aoi" o "geometry"
        aoi = payload.get("aoi") or payload.get("geometry") or {}
        bbox = aoi.get("bbox") if isinstance(aoi, dict) else None

    if not bbox:
        return None

    centroid = bbox_centroid(bbox)
    if not centroid:
        return None

    lat, lon = centroid
    return latlon_to_hex(lat, lon)
