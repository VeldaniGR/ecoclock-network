"""Cliente mínimo CDSE: token OAuth para catálogo / descargas."""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.config import settings

_token: str | None = None
_token_expires_at: float = 0.0


class CopernicusConfigError(RuntimeError):
    """Faltan credenciales CDSE en .env."""


class CopernicusAuthError(RuntimeError):
    """No se pudo obtener el access_token."""


def _credentials_configured() -> bool:
    return bool(settings.CDSE_USERNAME and settings.CDSE_PASSWORD)


def get_cdse_token(*, force_refresh: bool = False) -> str:
    """Devuelve un access_token de CDSE (con caché en memoria)."""
    global _token, _token_expires_at

    if not _credentials_configured():
        raise CopernicusConfigError(
            "CDSE_USERNAME / CDSE_PASSWORD no configurados en .env"
        )

    now = time.time()
    if not force_refresh and _token and now < (_token_expires_at - 60):
        return _token

    data = {
        "client_id": settings.CDSE_CLIENT_ID,
        "username": settings.CDSE_USERNAME,
        "password": settings.CDSE_PASSWORD,
        "grant_type": "password",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                settings.CDSE_TOKEN_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.HTTPError as exc:
        raise CopernicusAuthError(f"Error de red al pedir token CDSE: {exc}") from exc

    if response.status_code != 200:
        raise CopernicusAuthError(
            f"CDSE auth falló HTTP {response.status_code}: {response.text[:300]}"
        )

    payload: dict[str, Any] = response.json()
    access = payload.get("access_token")
    if not access:
        raise CopernicusAuthError("Respuesta CDSE sin access_token")

    expires_in = int(payload.get("expires_in") or 600)
    _token = access
    _token_expires_at = now + expires_in
    return access


def cdse_auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {get_cdse_token()}"}

STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"


def search_sentinel2_l2a(
    *,
    bbox: list[float],
    datetime_range: str,
    max_cloud: float = 30.0,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Busca productos Sentinel-2 L2A en el catálogo STAC de CDSE.

    bbox: [min_lon, min_lat, max_lon, max_lat]  (EPSG:4326)
    datetime_range: "2024-06-01T00:00:00Z/2024-08-31T23:59:59Z"
    """
    body: dict[str, Any] = {
        "collections": ["sentinel-2-l2a"],
        "bbox": bbox,
        "datetime": datetime_range,
        "limit": limit,
        "query": {
            "eo:cloud_cover": {"lt": max_cloud},
        },
    }

    headers = {
        **cdse_auth_headers(),
        "Content-Type": "application/json",
        "Accept": "application/geo+json",
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(STAC_SEARCH_URL, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise CopernicusAuthError(f"Error de red en STAC search: {exc}") from exc

    if response.status_code == 401:
        raise CopernicusAuthError("STAC search: no autorizado (revisa token CDSE)")
    if response.status_code >= 400:
        raise CopernicusAuthError(
            f"STAC search HTTP {response.status_code}: {response.text[:400]}"
        )

    data = response.json()
    features = data.get("features") or []
    results: list[dict[str, Any]] = []
    for feat in features:
        props = feat.get("properties") or {}
        results.append(
            {
                "id": feat.get("id"),
                "datetime": props.get("datetime"),
                "cloud_cover": props.get("eo:cloud_cover"),
                "bbox": feat.get("bbox"),
                "assets": list((feat.get("assets") or {}).keys()),
            }
        )
    return results


def build_posidonia_payload(
    *,
    product_id: str,
    bbox: list[float],
    cloud_cover: float | None = None,
    datetime_str: str | None = None,
    unit_id: str | None = None,
) -> dict[str, Any]:
    """Payload de tarea tipo posidonia alineado con tasks/posidonia/README.md."""
    uid = unit_id or f"POS-{product_id[-12:]}"
    return {
        "type": "posidonia",
        "version": 1,
        "unit_id": uid,
        "region": "Illes Balears",
        "bbox": {
            "min_lon": bbox[0],
            "min_lat": bbox[1],
            "max_lon": bbox[2],
            "max_lat": bbox[3],
            "crs": "EPSG:4326",
        },
        "source": {
            "name": "copernicus_sentinel2",
            "collection": "sentinel-2-l2a",
            "product_id": product_id,
            "datetime": datetime_str,
            "cloud_cover": cloud_cover,
            "provider": "CDSE",
            "stac": "https://stac.dataspace.copernicus.eu/v1",
        },
        "params": {
            "metric": "surface_m2",
            "method": "placeholder",
            "notes": (
                "Beta: el cliente puede devolver un resultado simulado. "
                "Fuente satélite: Copernicus Sentinel-2 L2A (no GFW ni Atlas API)."
            ),
        },
        "description": (
            "Estimar superficie de Posidonia oceanica en la unidad indicada "
            "a partir de escena Sentinel-2 (CDSE)."
        ),
    }
